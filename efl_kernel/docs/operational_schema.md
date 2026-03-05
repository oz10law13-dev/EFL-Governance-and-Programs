# Operational Schema — EFL Kernel

## 1. Purpose

This document defines the persisted data sources required to satisfy
the current `KernelDependencyProvider` contract and the current live
gate logic. Every entity, table, and field documented here is directly
traceable to a method call or field access in one of the following
source files:

- `efl_kernel/kernel/dependency_provider.py`
- `efl_kernel/kernel/gates_scm.py`
- `efl_kernel/kernel/gates_meso.py`
- `efl_kernel/kernel/gates_macro.py`
- `efl_kernel/kernel/gates_cl.py`
- `efl_kernel/kernel/kernel.py`
- `efl_kernel/kernel/audit_store.py`

Nothing is defined speculatively. If no current gate or kernel method
reads a field, that field does not appear in this document.

---

## 2. Dependency contract map

### get_athlete_profile(athlete_id) → dict

- **Status:** consumed by live gates
- **Callers:**
  - `gates_scm.py` line 29 — reads `maxDailyContactLoad` for `SCM.MAXDAILYLOAD`
  - `gates_scm.py` line 48 — reads `minimumRestIntervalHours` for `SCM.MINREST`
  - `gates_cl.py` line 19–20 — reads `e4_clearance` for `CL.CLEARANCEMISSING`
- **Expected return:** a dict containing at minimum `maxDailyContactLoad`,
  `minimumRestIntervalHours`, and `e4_clearance`. Missing keys fall back to
  fail-open defaults in the current `InMemoryDependencyProvider` (see section 3).

### get_prior_session(athlete_id, before_date) → dict | None

- **Status:** consumed by live gate
- **Callers:**
  - `gates_scm.py` line 45 — retrieves the most recent prior session to compute
    elapsed hours for `SCM.MINREST`
- **Expected return:** a dict containing at minimum `sessionDate` (ISO 8601
  datetime string), or `None` if no qualifying prior session exists.

### get_window_totals(athlete_id, window_type, anchor_date, exclude_session_id) → dict

- **Status:** consumed by live gate
- **Callers:**
  - `gates_meso.py` line 14 — requests `ROLLING28DAYS` totals for `MESO.LOADIMBALANCE`
- **Expected return:** a dict with keys `totalContactLoad` (float) and
  `dailyContactLoads` (list of floats, one entry per session in the window,
  in ascending date order).

### get_weekly_totals(athlete_id, anchor_date) → dict

- **Status:** UNCONSUMED — no current live gate reads this method
- No gate in `gates_scm.py`, `gates_meso.py`, `gates_macro.py`, or `gates_cl.py`
  calls this method. It must not drive any table or field definition in Phase 10.
  It is a reserved future contract slot only. See section 9 for full detail.

### get_season_phases(athlete_id, season_id) → dict

- **Status:** consumed by live gate
- **Callers:**
  - `gates_macro.py` line 10 — retrieves `competitionWeeks` and `gppWeeks` for
    `MACRO.PHASEMISMATCH`
- **Expected return:** a dict with keys `competitionWeeks` (numeric) and
  `gppWeeks` (numeric).

### get_override_history(lineage_key, module_id, window_days) → dict

- **Status:** consumed by kernel.py directly (not a gate)
- **Callers:**
  - `kernel.py` line 145 — Step 9, override cap breach check for
    `RAL.OVERRIDEREASONCAPBREACH` and `RAL.OVERRIDEVIOLATIONCAPBREACH`
  - `kernel.py` line 158 — Step 10, REVIEW-OVERRIDE-CLUSTER threshold check
- **Expected return:** a dict with keys `byReasonCode` (dict mapping reason
  code → count) and `byViolationCode` (dict mapping violation code → count).
- **Resolution:** this method resolves through `AuditStore.get_override_history()`,
  which queries the `override_ledger` table already owned by `audit_store.py`.
  No new operational table is needed.

---

## 3. Entity: Athlete

**Provider method:** `get_athlete_profile(athlete_id) → dict`
**Gate consumers:** `gates_scm.py` (SCM.MAXDAILYLOAD, SCM.MINREST), `gates_cl.py` (CL.CLEARANCEMISSING)

### Columns

| Column | Type | Constraints |
|--------|------|-------------|
| `athlete_id` | TEXT | PRIMARY KEY NOT NULL |
| `max_daily_contact_load` | REAL | NOT NULL |
| `minimum_rest_interval_hours` | REAL | NOT NULL |
| `e4_clearance` | INTEGER | NOT NULL — 0 = False, 1 = True |
| `created_at` | TEXT | NOT NULL — UTC ISO 8601 datetime |
| `updated_at` | TEXT | NOT NULL — UTC ISO 8601 datetime |

### Field traceability

**`max_daily_contact_load`**
- Read at `gates_scm.py` line 35:
  `max_daily = athlete_profile.get("maxDailyContactLoad", float("inf"))`
- Used on line 36: `if contact_load > float(max_daily):` — triggers `SCM.MAXDAILYLOAD`
  when the session's computed contact load exceeds the athlete's daily cap.
- `InMemoryDependencyProvider` default when field absent: `float("inf")` — **fail-open**:
  any contact load passes the gate for an unknown athlete.

**`minimum_rest_interval_hours`**
- Read at `gates_scm.py` line 48:
  `min_rest_hours = float(athlete_profile.get("minimumRestIntervalHours", 24))`
- Used on lines 49–50: elapsed hours between prior session and current session
  is compared against this value — triggers `SCM.MINREST` if below threshold.
- `InMemoryDependencyProvider` default when field absent: `24` — **fail-open**:
  a 24-hour minimum is applied for unknown athletes, which may be permissive
  depending on sport context.

**`e4_clearance`**
- Read at `gates_cl.py` line 20:
  `has_clearance = bool(athlete_profile.get("e4_clearance", False))`
- Used on line 28: exercises marked `e4_requires_clearance = True` in the
  exercise library trigger `CL.CLEARANCEMISSING` if `has_clearance` is False.
- `InMemoryDependencyProvider` default when field absent: `False` — **fail-open**:
  no clearance is assumed, which means E4-restricted exercises will be blocked.
  This default is actually fail-closed for the clearance gate specifically.

### Fail-closed requirement

When `athlete_id` is not found in the store, the real SQLite provider in Phase 11
must **not** return a dict with permissive defaults. Returning `float("inf")` for
`max_daily_contact_load` means any session passes `SCM.MAXDAILYLOAD` for an unknown
athlete. This is fail-open and must not occur in production.

The Phase 11 provider must raise or return a structured deny result when
`athlete_id` is not found.

**Structured deny result** for a missing athlete: return a dict with
`max_daily_contact_load = 0.0`. A load cap of zero forces an immediate
`SCM.MAXDAILYLOAD` violation on any session with nonzero contact load.
This is the correct fail-closed behavior — an unknown athlete cannot pass
the load gate.

---

## 4. Entity: Session

**Provider methods:**
- `get_prior_session(athlete_id, before_date) → dict | None`
- `get_window_totals(athlete_id, window_type, anchor_date, exclude_session_id) → dict`

**Gate consumers:**
- `gates_scm.py` reads `get_prior_session` for `SCM.MINREST`
- `gates_meso.py` reads `get_window_totals` for `MESO.LOADIMBALANCE`

### Columns

| Column | Type | Constraints |
|--------|------|-------------|
| `session_id` | TEXT | PRIMARY KEY NOT NULL |
| `athlete_id` | TEXT | NOT NULL — FK → athletes.athlete_id |
| `session_date` | TEXT | NOT NULL — UTC ISO 8601 datetime |
| `contact_load` | REAL | NOT NULL |

### Field traceability

**`session_id`**
- Used as `exclude_session_id` in `get_window_totals` calls — the session being
  evaluated is excluded from its own rolling window to prevent self-inclusion.
  Corresponds to the payload's `objectID` for SESSION evaluations.

**`athlete_id`**
- Partition key for both provider queries. Read from `evaluationContext.athleteID`
  in the payload (`gates_scm.py` line 28, `gates_meso.py` line 9).

**`session_date`**
- Read by `get_prior_session` to order and filter qualifying prior sessions.
  Read at `gates_scm.py` line 46:
  `prior_dt = _parse_dt((prior or {}).get("sessionDate"))`
- Used as the boundary for rolling-window membership in `get_window_totals`.
- Stored as a UTC ISO 8601 datetime string.

**`contact_load`**
- Aggregated by `get_window_totals` into `totalContactLoad` (sum) and
  `dailyContactLoads` (list). Consumed at `gates_meso.py` line 15:
  `daily = [float(x) for x in totals.get("dailyContactLoads", [])]`

### Prior-session query semantics

```sql
SELECT *
FROM sessions
WHERE athlete_id = ?
  AND session_date < before_date
ORDER BY session_date DESC
LIMIT 1
```

Returns `None` if no qualifying row exists. Strict less-than — the session
being evaluated is excluded by timestamp, not by `session_id`. Ties
(two sessions at the exact same timestamp) are broken by row insertion order;
the last-inserted row wins.

### Rolling-window query semantics for get_window_totals

```sql
SELECT session_date, contact_load
FROM sessions
WHERE athlete_id = ?
  AND session_id != exclude_session_id
  AND session_date >= window_start
  AND session_date <= anchor_date
ORDER BY session_date ASC
```

- `window_start` = `anchor_date` minus `window_days`
  - `ROLLING28DAYS`: 28 days back from anchor
  - `ROLLING7DAYS`: 7 days back from anchor
- Returns:
  - `totalContactLoad` = `SUM(contact_load)` over qualifying rows
  - `dailyContactLoads` = list of `contact_load` values in ascending date order
- The session being evaluated is excluded via `exclude_session_id` to prevent
  its own load from appearing in its own rolling average.

---

## 5. Entity: Season

**Provider method:** `get_season_phases(athlete_id, season_id) → dict`
**Gate consumer:** `gates_macro.py` (MACRO.PHASEMISMATCH)

### Columns

| Column | Type | Constraints |
|--------|------|-------------|
| `season_id` | TEXT | NOT NULL |
| `athlete_id` | TEXT | NOT NULL — FK → athletes.athlete_id |
| `competition_weeks` | INTEGER | NOT NULL |
| `gpp_weeks` | INTEGER | NOT NULL |
| `start_date` | TEXT | NOT NULL — UTC ISO 8601 date |
| `end_date` | TEXT | NOT NULL — UTC ISO 8601 date |
| `created_at` | TEXT | NOT NULL — UTC ISO 8601 datetime |
| `updated_at` | TEXT | NOT NULL — UTC ISO 8601 datetime |

**PRIMARY KEY:** `(athlete_id, season_id)`

### Gate logic that consumes these values

From `gates_macro.py` lines 10–15:

```python
phases = dep_provider.get_season_phases(athlete_id, season_id)
competition_weeks = float(phases.get("competitionWeeks", 0) or 0)
gpp_weeks = float(phases.get("gppWeeks", 0) or 0)

if competition_weeks > 0 and (gpp_weeks <= 0 or (competition_weeks / gpp_weeks) > 2.0):
    violations.append({"code": "MACRO.PHASEMISMATCH", ...})
```

Two conditions fire `MACRO.PHASEMISMATCH`:
1. `competition_weeks > 0` and `gpp_weeks <= 0` — competition load exists but
   no GPP base work recorded.
2. `competition_weeks > 0` and `competition_weeks / gpp_weeks > 2.0` — competition
   weeks exceed twice the GPP weeks.

### Fail-open gap

When `(athlete_id, season_id)` is not found, `InMemoryDependencyProvider` currently
returns `{"competitionWeeks": 0, "gppWeeks": 0}`. With both values at zero,
`competition_weeks > 0` is `False` and the gate does not fire. A missing season
record silently passes `MACRO.PHASEMISMATCH`. This is fail-open.

The Phase 11 provider must **not** return these defaults for a missing record.
A missing season must fail closed.

**Structured deny result** for a missing season: return
`{"competitionWeeks": 1, "gppWeeks": -1}`. This satisfies both conditions
simultaneously — `competition_weeks > 0` is True and `gpp_weeks <= 0` is True —
guaranteeing `MACRO.PHASEMISMATCH` fires immediately for any missing season
record regardless of evaluation context.

Alternatively, the Phase 11 provider may raise a structured exception that the
kernel's missing-dependency handling converts to the appropriate synthetic
violation. Either approach is acceptable; the requirement is that a missing
`(athlete_id, season_id)` pair never silently passes the MACRO gate.

---

## 6. Override history — audit-owned

Override history is already owned by `audit_store.py` via the `override_ledger`
table. `get_override_history()` resolves through `AuditStore.get_override_history()`,
which queries `override_ledger` with a rolling time window.

### Existing audit_store.py tables (for reference)

**`kdo_log`**
- One record per committed KDO
- Columns: `decision_hash` (PK), `timestamp_normalized`, `module_id`,
  `object_id`, `kdo_json`

**`override_ledger`**
- One record per override per committed KDO
- Columns: `lineage_key`, `module_id`, `violation_code`, `reason_code`,
  `timestamp_normalized`
- Composite PK: `(lineage_key, module_id, violation_code, reason_code, timestamp_normalized)`

Phase 10 must not touch these tables or redefine their DDL. No new operational
table is needed for override history.

---

## 7. Empty-window policy decision

### Current code behavior

When no session rows exist in the rolling window, `get_window_totals` returns:

```python
{"totalContactLoad": 0.0, "dailyContactLoads": []}
```

The MESO gate (`gates_meso.py` line 16) evaluates imbalance only when
`len(daily) >= 2`. An empty list suppresses the gate entirely — no violation
is produced.

### Adopted policy

**An empty window is a valid state.** It represents an athlete with no training
history in the window period — a new athlete, a returning athlete after a long
gap, or a fresh mesocycle start. The empty-window shape is the correct neutral
return and the MESO gate correctly suppresses.

The fail-closed case is a **missing athlete record**, not a missing window.
An athlete who exists in the store but has no sessions in the window is a
clean state. An `athlete_id` that does not exist in the athletes store at all
is the deny trigger.

This decision must be preserved in Phase 11 implementation:

- Missing athlete → fail closed (deny result or raise)
- Athlete exists, no sessions in window → neutral shape `{"totalContactLoad": 0.0, "dailyContactLoads": []}`, gate suppresses naturally

---

## 8. Timestamp and bucketing semantics

The following rules are canonical and locked. All Phase 10 and Phase 11
implementation must conform to them without exception.

### Storage format

- All datetimes: UTC ISO 8601 with offset — e.g. `"2026-01-15T14:30:00+00:00"`
- All dates: ISO 8601 date string — e.g. `"2026-01-15"`
- SQLite column type: `TEXT` for all timestamps and dates
- No UNIX epoch integers. No local-time strings.

### Prior-session ordering

- Strict less-than on `session_date` (`< before_date`)
- Most recent qualifying row: `ORDER BY session_date DESC LIMIT 1`
- Ties (identical `session_date` values) broken by row insertion order —
  last inserted wins

### Rolling-window boundaries

- Anchor date: the `anchorDate` from `windowContext` in the evaluation payload
  defines the window end boundary (inclusive)
- Window start: `anchor_date` minus `window_days` (inclusive)
- `ROLLING28DAYS`: 28 days back from anchor
- `ROLLING7DAYS`: 7 days back from anchor

### Day bucketing

- A session belongs to a window based on its UTC `session_date`
- No local-time conversion is applied
- Window boundary comparisons use string comparison on ISO 8601 formatted
  dates — lexicographic ordering is correct and sufficient for ISO 8601

### Self-exclusion

- The session being evaluated is excluded from its own rolling window via
  `exclude_session_id`
- This prevents a session from counting its own load against its own rolling
  average or imbalance calculation

---

## 9. Unconsumed contract: get_weekly_totals

| Attribute | Value |
|-----------|-------|
| Signature | `get_weekly_totals(athlete_id, anchor_date) → dict` |
| Current gate consumers | **None** |
| Current InMemoryDependencyProvider behavior | Returns four weekly buckets with `totalContactLoad = 0.0` |
| Schema impact | No table defined for this method in Phase 10 |
| Status | Reserved future contract slot only |
| Action required before Phase 10 implements it | A live gate must exist that reads this method |
| Phase 10 constraint | Must not create a `weekly_totals` table |

No file in `gates_scm.py`, `gates_meso.py`, `gates_macro.py`, or `gates_cl.py`
contains a call to `get_weekly_totals`. This method has no current gate consumer
and must not drive table design.

---

## 10. Provider-method-to-storage mapping

| Method | Source entity | Required keys | Output shape | Missing-record behavior |
|--------|---------------|---------------|--------------|------------------------|
| `get_athlete_profile` | `athletes` table | `athlete_id` | `{maxDailyContactLoad, minimumRestIntervalHours, e4_clearance}` | **Fail closed** — return deny dict with `max_daily_contact_load = 0.0` |
| `get_prior_session` | `sessions` table | `athlete_id`, `before_date` | `{sessionDate, ...}` or `None` | Returns `None` — gate suppresses (no prior session is valid for new athletes) |
| `get_window_totals` | `sessions` table | `athlete_id`, `window_type`, `anchor_date`, `exclude_session_id` | `{totalContactLoad, dailyContactLoads[]}` | Empty window → neutral shape `{0.0, []}` — gate suppresses (valid state, not a deny trigger) |
| `get_weekly_totals` | **UNCONSUMED** — no table | n/a | n/a | Not implemented in Phase 10 |
| `get_season_phases` | `seasons` table | `athlete_id`, `season_id` | `{competitionWeeks, gppWeeks}` | **Fail closed** — return deny dict with `{competitionWeeks: 1, gppWeeks: -1}` |
| `get_override_history` | `override_ledger` (audit_store) | `lineage_key`, `module_id`, `window_days` | `{byReasonCode{}, byViolationCode{}}` | Returns empty counts — no overrides recorded yet is a clean state |

---

## 11. Audit-store interaction note for Phase 10

`audit_store.py` already owns SQLite DDL and creates the following tables on
`AuditStore.__init__`: `kdo_log`, `override_ledger`.

Phase 10 must read `audit_store.py` in full before writing any DDL. It must:

- Follow the same `CREATE TABLE IF NOT EXISTS` pattern used in `audit_store.py`'s
  `_DDL` block
- Use the same database file as `AuditStore` — one shared SQLite file for both
  audit and operational tables
- Not create a second database
- Not reuse table names already owned by `audit_store.py` (`kdo_log`,
  `override_ledger`)

Operational tables (`athletes`, `sessions`, `seasons`) and audit tables
(`kdo_log`, `override_ledger`) share the same database file but remain separate
in responsibility. No joins between operational and audit tables are required
or permitted in provider queries.

---

## 12. Phase 12 seed requirement

Phase 12 requires demonstrating a real persisted end-to-end evaluation with
zero injected fixtures. This cannot be done without a way to insert athlete,
session, and season records into the operational database before running the CLI.

Phase 10 must therefore include a minimal data-seeding mechanism — a script or
CLI subcommand — that accepts a JSON fixture file and writes the defined entities
(`athletes`, `sessions`, `seasons`) into the operational SQLite store.

This is not a builder. It does not generate training programs. Its only purpose
is test-data insertion to enable Phase 12 and Phase 13 to operate against real
persisted state.

Do not design or build the seed tool in Phase 9. This section records the
requirement so Phase 10 includes it in scope.

---

## 13. Explicit non-goals

This document does not cover and Phase 9 has not produced:

- SQLite table creation or DDL
- Python migrations
- Provider implementation code
- CLI changes
- FastAPI or HTTP service layer
- Artifact persistence or publish runtime
- GOVERNANCE gate logic or spec
- Builder or training program generation logic
- Handshake spec, DCC spec, Output Spec
- Frontend, tenancy, or PostgreSQL migration path
- Materialized totals tables
- Mesocycle entity or table (`mesoID` is an evaluation context identifier only)
- Weekly totals table
- Any field without a current live gate consumer
