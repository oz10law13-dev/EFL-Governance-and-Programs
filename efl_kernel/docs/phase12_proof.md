# Phase 12 — Persisted End-to-End Evaluation Proof

Demonstrates that SESSION, MESO, and MACRO evaluations run against
real persisted SQLite state via SqliteDependencyProvider, with zero
injected fixtures, and that KDOs are persisted to the audit store.

---

## Prerequisites

Python environment active, repo root as working directory.

```
python -m pytest -q
```

Expected: all tests pass (baseline 77 before Phase 12).

---

## Step 1 — Create database and seed

```
python -m efl_kernel.tools.seed \
  --db efl_audit.db \
  --fixture efl_kernel/tools/fixtures/sample_seed.json
```

Expected output:
```
Seeded: 2 athletes, 9 sessions, 2 seasons → efl_audit.db
```

ATH001: max_daily_contact_load=150.0, e4_clearance=0, 5 sessions.
ATH002: max_daily_contact_load=80.0, e4_clearance=1, 4 sessions with
a spike (contact_load=150.0 on 2026-01-26). Season SEASON-2026:
competition_weeks=10, gpp_weeks=2 (ratio 5.0 > 2.0).

---

## Step 2 — SESSION evaluation (CL violation)

Write the following JSON to `session_payload.json`:

```json
{
  "moduleVersion": "1.1.1",
  "moduleViolationRegistryVersion": "1.1.1",
  "registryHash": "e23fcaaf222a1a39dcb4905850954e458f89200288db0d2912e5ef1d0329710d",
  "objectID": "SMOKE-S-001",
  "evaluationContext": {
    "athleteID": "ATH001",
    "sessionID": "SMOKE-S-001"
  },
  "windowContext": [
    {
      "windowType": "ROLLING7DAYS",
      "anchorDate": "2026-01-01",
      "startDate": "2025-12-26",
      "endDate": "2026-01-01",
      "timezone": "UTC"
    },
    {
      "windowType": "ROLLING28DAYS",
      "anchorDate": "2026-01-01",
      "startDate": "2025-12-05",
      "endDate": "2026-01-01",
      "timezone": "UTC"
    }
  ],
  "session": {
    "sessionDate": "2026-03-01T10:00:00+00:00",
    "contactLoad": 0,
    "exercises": [{"exerciseID": "isometric_mid_thigh_pull_max"}]
  }
}
```

```
python -m efl_kernel.cli \
  --module SESSION \
  --input session_payload.json \
  --db efl_audit.db
```

Expected: KDO JSON with `"CL.CLEARANCEMISSING"` in `violations`.

ATH001 has `e4_clearance=0` (False). `isometric_mid_thigh_pull_max`
requires E4 clearance. contactLoad=0 does not trigger SCM.MAXDAILYLOAD
(cap=150). SessionDate 2026-03-01 is 34 days after ATH001's last
seeded session (2026-01-26), exceeding the 24-hour minimum rest
interval, so SCM.MINREST is also silent.

---

## Step 3 — MESO evaluation (load imbalance)

Write the following JSON to `meso_payload.json`:

```json
{
  "moduleVersion": "1.0.2",
  "moduleViolationRegistryVersion": "1.0.2",
  "registryHash": "54113cf2db1116bf67407da998c10c09d89a111d28dd25fd0baa3da03e36e7f5",
  "objectID": "SMOKE-MESO-OBJ-001",
  "evaluationContext": {
    "athleteID": "ATH002",
    "mesoID": "SMOKE-MESO-001"
  },
  "windowContext": [
    {
      "windowType": "MESOCYCLE",
      "anchorDate": "2026-02-01",
      "startDate": "2026-01-04",
      "endDate": "2026-02-01",
      "timezone": "UTC"
    }
  ]
}
```

```
python -m efl_kernel.cli \
  --module MESO \
  --input meso_payload.json \
  --db efl_audit.db
```

Expected: KDO JSON with `"MESO.LOADIMBALANCE"` in `violations`.

Note: `anchorDate` must be `"2026-02-01"`. The MESO gate reads
`anchorDate` from the MESOCYCLE window and uses it as the anchor for
a `ROLLING28DAYS` query: window covers `2026-01-04` through
`2026-02-01`. This captures all four ATH002 sessions:
[30.0, 35.0, 30.0, 150.0]. avg=61.25, max=150 > 122.5 (2x avg)
triggers MESO.LOADIMBALANCE. Any earlier anchor date risks missing
the spike session on 2026-01-26.

---

## Step 4 — MACRO evaluation (phase mismatch)

Write the following JSON to `macro_payload.json`:

```json
{
  "moduleVersion": "1.0.2",
  "moduleViolationRegistryVersion": "1.0.2",
  "registryHash": "dc52f54f1dfc0c1466d4285c61b9dbb6990bdd48629909de57a744fba6912e58",
  "objectID": "SMOKE-MACRO-OBJ-001",
  "evaluationContext": {
    "athleteID": "ATH002",
    "seasonID": "SEASON-2026"
  },
  "windowContext": [
    {
      "windowType": "SEASON",
      "anchorDate": "2026-12-31",
      "startDate": "2026-01-01",
      "endDate": "2026-12-31",
      "timezone": "UTC"
    }
  ]
}
```

```
python -m efl_kernel.cli \
  --module MACRO \
  --input macro_payload.json \
  --db efl_audit.db
```

Expected: KDO JSON with `"MACRO.PHASEMISMATCH"` in `violations`.

ATH002 season `SEASON-2026`: competition_weeks=10, gpp_weeks=2.
Ratio = 10/2 = 5.0 > 2.0. This is a real persisted season row,
not the fail-closed sentinel.

---

## Step 5 — Verify KDO persistence

```
sqlite3 efl_audit.db "SELECT COUNT(*) FROM kdo_log;"
```

Expected: `3`

---

## Architecture note

All violations above are produced from persisted SQLite state via
`SqliteDependencyProvider`. No in-memory fallback is active. No
`mock.patch` is used. No fixtures are injected into the provider.

ATH002 MESO violation comes from persisted `op_sessions` rows queried
by `get_window_totals` using the MESOCYCLE window's `anchorDate`.
ATH002 MACRO violation comes from the persisted `op_seasons` row
returned by `get_season_phases("ATH002", "SEASON-2026")`.
ATH001 CL violation comes from the persisted `op_athletes` row
(`e4_clearance=0`, coerced to `False` by the provider) combined with
the E4-restricted exercise in the evaluation payload.

The `SqliteDependencyProvider` uses fail-closed sentinels only for
missing records. All three smoke tests exercise real rows — none
rely on sentinel behavior.
