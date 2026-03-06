# DCC-Physique v1.2.1: Daily Constrained Conjugate for Hypertrophy Training
## Complete Enforceable Specification with ECA Integration & Frequency Hardening

---

## DOCUMENT METADATA

| Field | Value |
|-------|-------|
| **Document ID** | DCC-PHYSIQUE-v1.2.1 |
| **Version** | 1.2.1 |
| **Status** | OPERATIONAL – Fully Enforceable |
| **Effective Date** | 2026-01-26 |
| **Supersedes** | DCC-Physique v1.1-K-CORRECTED, v1.1 RC1/RC2, all prior drafts, DCC-Physique v1.2 |
| **Parent Authority** | DCC v2.2, EPA Exercise Progression Law v1.0.2, EFL Governance v4.1 |
| **ECA Dependency** | Exercise Classification Authority ECA v1.1-K with Patches K–P |
| **MCC Dependency** | Meso Constraint Controller v1.0.1 for 6× frequency enforcement |
| **Implementation Requirement** | Requires complete ECA coverage validator tooling + MCC v1.0.1 for 6×/week programs |

---

## CHANGE LOG

| Version | Date | Changes |
|---------|------|---------|
| v1.0-DRAFT | 2026-01-20 | Initial architecture draft |
| v1.0-RC1 | 2026-01-25 | Patch Groups A–B: Input Gate, H-Node mapping, mesocycle structure |
| v1.0-RC2 | 2026-01-25 | Patch Group D: Weekly Frequency Contract (3–6 governance) |
| v1.1 | 2026-01-25 | Patch Groups E–I: Hardening release; pattern balance, density ledger, reactive deload, chronic YELLOW guard |
| v1.1-K-CORRECTED | 2026-01-25 | Critical corrections: split-counting for dual-tags (0.5–0.5), frontal plane rule, NODE 3 pre-condition validation, terminology standardization, H3 session counting clarification |
| **v1.2** | **2026-01-26** | **Patch F: Frequency Hardening – Clarify 6× contract (B≤2 allowed with MCC adjacency/density controls); align with Program Framework v2.1; update Non-Negotiable Rules and reason codes.** |
| **v1.2.1** | **2026-01-26** | **Patch F Enforcement Completion – Formalize DCC↔MCC handshake (Pass order + required gates), add authority tie-break clause, add test vectors, and publish reason-code manifest for registry sync.** |

---

## SCOPE AND INTENT

DCC-Physique is a **containment-first hypertrophy system** for healthy adults ≥18 that prioritizes:

1. **Reliable hypertrophy stimulus** without junk volume
2. **Injury prevention** via density caps, readiness binding, and structural balance
3. **Auditability** across sessions, weeks, and mesocycles
4. **Enforceability** through external Exercise Classification Authority (ECA)

**DCC-Physique v1.2.1 is the definitive, implementation-ready specification.** All rules are deterministic, machine-enforceable, and closed to interpretation loopholes.

---

## AUTHORITY HIERARCHY

1. **EFL Governance v4.1** – Organizational top-level law
2. **DCC v2.2** – Session structure, block budgets, PRIME binding, readiness modifiers
3. **DCC-Physique v1.2.1** (This document) – Physique-specific adaptations, frequency hardening (Patch F), and DCC↔MCC enforcement handshake (Patch F-04)
4. **EPA Exercise Progression Law v1.0.2** – ONEAXISATATIME progression binding
5. **Exercise Classification Authority ECA v1.1-K** – Exercise metadata, enforcement rules, permission gates
6. **Meso Constraint Controller (MCC) v1.0.1** – Long-horizon accumulation, adjacency, density, route saturation (for 6× programs)
7. **Block Documents** – Mesocycle templates, phase structure

**Conflict Resolution Rule:** Always apply the most restrictive rule **unless** this document explicitly grants a scoped exception (e.g., 6× B2 under Patch F).

**Authority Tie-Break Clause (Generator vs Law):** Program Framework v2.1 (and any other generator/template document) is **non-authoritative**. If a framework’s frequency composition, sequencing, or example template conflicts with this document, the framework is wrong by definition and must be patched. The only valid way to legalize a framework variance is an explicit patch in this document (e.g., Patch F for 6× B≤2).

---

# 1. POPULATION AND RISK PROFILE

## 1.1 Target Population

- Adults ≥18 with hypertrophy/physique as primary training goal
- No active injury or unresolved joint pain
- Cleared for resistance training by medical professional (if applicable)
- Goal: muscle growth, aesthetics, training longevity

## 1.2 Risk Factors This System Addresses

- **Training monotony** – adaptation plateau, boredom, dropout
- **Overuse injuries** – cumulative joint/tendon stress without legality violation
- **Recovery debt** – systemic fatigue, hormonal suppression, illness despite compliance
- **Volume mismanagement** – junk volume without meaningful stimulus
- **Structural imbalance** – postural dysfunction, chronic pain, aesthetic asymmetry
- **Chronic fatigue tolerance** – progressive degradation masked by formal legality
- **Density stacking** – near-maximal neural load without BAND 3 exposure

## 1.3 Not Applicable

- Youth-specific constraints (skeletal maturity gates, load restrictions)
- Plyometric/elastic training caps (de-emphasized in hypertrophy)
- Sport-specific performance markers
- Acute injury rehabilitation protocols (see R2P pathways)

## 1.4 Physique-Specific Constraints Enforced

- Set-based volume landmarks with muscle-group specificity
- Accumulated fatigue monitoring via readiness states
- Structural balance requirements (push/pull, horizontal/vertical, frontal plane, primary/corrective ratios)
- Pattern rotation enforcement (Day C anti-repetition)
- Aggregate density tracking (BAND 2–NODE 3 exposure, total NODE 3 volume)
- Reactive deload triggers (collapse patterns, chronic readiness degradation)
- Volume classification with deterministic, immutable test
- Exercise coverage completeness via ECA
- Day D intent lock with whitelist enforcement
- NODE 3 opt-in permission system
- Weekly frequency governance (3–6 training days)

---

# 2. BAND–NODE–H-NODE SYSTEM FOR HYPERTROPHY

## 2.1 Band Classification (Load Magnitude)

| Band | Load Range (% 1RM) | Primary Application | Typical Rep Range |
|------|-------------------|-------------------|------------------|
| **BAND 0** | 0–25 (bodyweight, activation) | Mobility, tissue prep, nervous system priming, movement quality | 15–30 |
| **BAND 1** | 25–60 (light–moderate) | Metabolic stress, motor learning, isolation work, capacity building | 12–25 |
| **BAND 2** | 60–80 (moderate–heavy) | Volume-load optimization, hypertrophy zone, submaximal work | 6–12 |
| **BAND 3** | ≥80 (heavy–maximal) | Mechanical tension, strength consolidation, peak force expression | 1–6 |

## 2.2 Node Classification (Density, Tempo)

| Node | Density (reps/min) | Rest Periods | Primary Application |
|------|-------------------|--------------|-------------------|
| **NODE 1** | 4–6 reps/min | 3–5 min | Technical mastery, eccentric focus, strength work, peak force |
| **NODE 2** | 8–12 reps/min | 2–3 min | **Hypertrophy sweet spot**, standard tempo, volume accumulation |
| **NODE 3** | ≥15 reps/min | ≤90 sec | Metabolic accumulation, supersets, circuits, density work |

## 2.3 H-Node (Hypertrophy Complexity)

| H-Node | Complexity Level | Typical Application | Neural Load |
|--------|-----------------|-------------------|-------------|
| **H0** | Isometric holds, slow eccentrics (≥5 sec tempo) | Tendon tolerance, time-under-tension, positional strength | Low |
| **H1** | Standard bilateral compound | Squat, bench, deadlift, row patterns (single exercise, standard tempo) | Low–Moderate |
| **H2** | Unilateral compound | Split squat, single-arm press, single-leg RDL (stability demand) | Moderate |
| **H3** | Hybrid/density techniques | Supersets, pre-exhaust, density circuits, drop sets (velocity-tolerant) | High |
| **H4** | Advanced techniques | Rest-pause, myo-reps, clusters, drop sets (peak intensity, CNS stress) | Very High |

## 2.4 H-Node Force–Velocity Mapping

| H-Node | Primary Bias | Typical Use Case |
|--------|------------|-----------------|
| **H0** | Force | Isometric tempo, tendon tolerance, positional strength, rehab |
| **H1** | Force-dominant | Mechanical tension, standard compound movements |
| **H2** | Mixed force–stability | Unilateral control, asymmetry correction |
| **H3** | Velocity-tolerant | Density work, metabolic stress, time-efficient stimulus |
| **H4** | Velocity–CNS | Neural stress, failure manipulation, peak intensity expression |

## 2.5 Adult Ceilings (Non-Negotiable)

| Parameter | Ceiling | Condition |
|-----------|---------|-----------|
| **BAND 3 readiness gate** | GREEN only | Any YELLOW/RED → max BAND 2 |
| **BAND 3 + NODE 3 simultaneous** | ILLEGAL | Combinations not allowed |
| **BAND 3 patterns per session** | 1 movement pattern | Prevents hidden CNS overload |
| **H4 blocks per week** | 1 WORK block | Across entire microcycle |
| **H3 sessions per week** | 3 sessions | See Section 6.4 for session definition |
| **NODE 3 permission** | ECA nodemax ≥3 required | Default illegal (Patch P-01) |

---

# 3. DAY-ROLE ARCHITECTURE FOR PHYSIQUE

**Critical Principle:** Frequency redistributes day roles; it does not modify their definitions or legality rules.

## 3.1 DAY A: Primary Compound Mechanical Tension

| Parameter | Specification |
|-----------|---------------|
| **Primary Intent** | Maximal force production, mechanical tension, strength expression |
| **Band ceiling** | BAND 2–3 (BAND 3 only with GREEN readiness) |
| **Node ceiling** | NODE 1–2 |
| **H-Node ceiling** | H1–H2 |
| **Pattern guarantee** | ≥3 compound patterns from {squat, hinge, press, pull} |
| **Volume target** | 40–60 working reps total (WORK block only) |
| **Typical set range** | 10–15 working sets |
| **Frequency limit** | **1 per week (non-negotiable)** |

**Illegal on DAY A:**
- <3 compound patterns
- NODE 3 usage
- H3 or H4 behaviors
- BAND 3 with YELLOW/RED readiness

---

## 3.2 DAY B: Secondary Hypertrophy Metabolic Accumulation

| Parameter | Specification |
|-----------|---------------|
| **Primary Intent** | Volume accumulation, metabolic stress, time-under-tension |
| **Band ceiling** | BAND 1–2 |
| **Node ceiling** | NODE 2–3 (if permitted per ECA) |
| **H-Node ceiling** | H1–H3 |
| **Pattern guarantee** | 5–6 exercises, balanced push/pull distribution; isolation emphasis allowed |
| **Volume target** | 60–90 working reps total (WORK block only) |
| **Typical set range** | 15–22 working sets |
| **Frequency limit** | **≤1 per week (strict) at 3–5×/week; ≤2 at 6× (v1.2 Patch F)** |
| **PRIME intent** | Joint prep for loaded ranges; tissue priming for peak force demands |

**Typical on DAY B:**
- Supersets (H3, antagonist muscles)
- Unilateral work (H2)
- Isolation exercises
- Higher rep ranges (10–20)

**Illegal on DAY B:**
- Only applies at 3–5× if B appears >1/week
- At 6×: DAY B ≤2 allowed if MCC adjacency (no B→B) and density ledger GREEN/YELLOW

---

## 3.3 DAY C: Structural Balance, Weak Points, Asymmetry Correction

| Parameter | Specification |
|-----------|---------------|
| **Primary Intent** | Address imbalances, weak points, postural deficits, lagging muscle groups |
| **Band ceiling** | BAND 0–2 |
| **Node ceiling** | NODE 2–3 (if permitted per ECA) |
| **H-Node ceiling** | H1–H3 |
| **Pattern guarantee** | Address structural imbalances: rear delts, hamstrings, glutes, rotator cuff, frontal plane, unilateral deficits |
| **Volume target** | 50–70 working reps total (WORK block only) |
| **Typical set range** | 12–18 working sets |
| **Frequency** | Variable: 1–3 per week depending on total frequency |
| **PRIME intent** | Movement quality prep for corrective patterns |

**Examples of DAY C Focus:**
- Posterior chain emphasis (hamstrings, glutes, rear delts)
- Unilateral leg work (frontal plane demand)
- Rotator cuff and scapular stability
- Core/trunk anti-rotation
- Corrective movement patterns

**Whitelist Enforcement (Patch O-01):** Only exercises with `day_roles_allowed` containing C in ECA are legal.

---

## 3.4 DAY D: Active Recovery, Regeneration

| Parameter | Specification |
|-----------|---------------|
| **Primary Intent** | Recovery, mobility, blood flow, parasympathetic restoration |
| **Band ceiling** | BAND 0–1 |
| **Node ceiling** | NODE 1–2 |
| **H-Node ceiling** | H0–H1 |
| **Pattern guarantee** | Mobility drills, low-level movement variability, tissue health |
| **Volume target** | 20–40 reps (RPE ≤4, no meaningful fatigue) |
| **Frequency** | 1 at 5×/week; **2 at 6×/week (mandatory, v1.2 Patch F)** |
| **PRIME intent** | Global tissue prep, low-level nervous system activation |

**Intent Lock (Patch E-02):** Cannot use tempo, ROM, or exercise selection to disguise hypertrophy stimulus.

**Always Illegal on DAY D:**
- Exercises not on ECA Day D whitelist
- Tempo manipulation to create hypertrophy stimulus (e.g., 5-0-5 on recovery exercise)
- ROM manipulation to increase difficulty
- Load beyond BAND 1
- Any exercise taken near failure (RPE >4)

**Violation Code:** `MCC_DAY_D_INTENT_VIOLATION`

---

# 4. WEEKLY FREQUENCY CONTRACT & VOLUME GOVERNANCE

## 4.1 Supported Frequencies

**DCC-Physique v1.2.1 supports exactly 4 training frequencies: 3, 4, 5, or 6 days per week.** Any other frequency (1, 2, 7, variable) = invalid.

Training frequency governs deployment and sequencing of fixed day roles (A, B, C, D). **Day role definitions, intent, ceilings, and legality do NOT change with frequency.** Frequency increases distribution, not permission.

---

## 4.2 Day-Role Allocation Matrix (v1.2 Patch F)

| Weekly Frequency | Required Day Roles | Hard Limits | Notes |
|-----------------|-------------------|-------------|-------|
| **3** | A1, B1, C1 | A=1, B=1, C=1 | Minimum viable; no D required |
| **4** | A1, B1, C1–2, D0–1 | A=1, B=1, C=1 | Additional C or D |
| **5** | A1, B1, C1–2, D≥1 | A=1, B=1, D=1 (min) | D-minimum enforced |
| **6** | A1, B≤2, C1, D≥2 | A=1, B≤2 (allowed), D=2 (mandatory) | **v1.2 Patch F: B=2 allowed if MCC adjacency (no B→B) + density ledger GREEN/YELLOW** |

### Non-Negotiable Rules (v1.2 Patch F)

- **DAY A maximum 1 per week** – Prevents CNS overload
- **DAY B:**
  - **3–5×/week: maximum 1 per week** – Prevents density saturation
  - **6×/week: ≤2 allowed** – Requires MCC Pass 2 enforcement (adjacency, density ledger)
- **Additional sessions beyond A+B (and the optional 6× second DAY B permitted by Patch F) must be DAY C or DAY D only**
- **D-minimum rule (Section 4.4):**
  - 3×: optional (0 required)
  - 4×: recommended (0–1)
  - 5×: mandatory (≥1 required)
  - 6×: **mandatory (≥2 required)**

**Reason Codes (DCC Pass 1):** `MCC_FREQUENCY_NOT_SUPPORTED`, `MCC_DAY_A_FREQUENCY_EXCEEDED`, `MCC_DAY_B_FREQUENCY_EXCEEDED`, `MCC_D_MINIMUM_VIOLATED`

**Patch F Enforcement Note:** When `frequency_per_week = 6` and `DAY_B_count = 2`, the weekly plan is **conditionally legal** and MUST be escalated to **MCC Pass 2**. If MCC Pass 2 fails adjacency/density gates, the plan is rejected (see Appendix F-04).

---

## 4.3 Weekly Volume Distribution Rule

Weekly volume landmarks (Section 8) remain authoritative:
- **Major muscle groups:** 10–20 sets/week
- **Minor muscle groups:** 8–16 sets/week
- **Postural/stability:** 6–12 sets/week

**Critical Rule:** Increasing frequency redistributes weekly volume **it does NOT expand landmark ceilings.**

| Frequency | Typical Sets/Session | Weekly Total Guidance |
|-----------|---------------------|----------------------|
| **3** | 18–24 | 54–72 |
| **4** | 15–22 | 60–88 |
| **5** | 12–18 | 60–90 |
| **6** | 10–16 | 60–96 |

**Per-Session Hard Cap:** 25 working sets always enforced, regardless of frequency.

**Volume Classification Rule (Patch G-02 + M-01):** Postural/stability work that materially loads primary muscle groups counts toward that group's landmark ceiling. Classification is immutable once assigned in ECA (Section 8, Patch M).

---

## 4.4 D-Minimum Rule: Mandatory Recovery Scheduling

At higher training frequencies, mandatory recovery days prevent chronic fatigue accumulation.

| Frequency | D-Minimum | Enforcement |
|-----------|-----------|-------------|
| **3** | 0 | Optional (not required) |
| **4** | 0–1 | Recommended (not required) |
| **5** | ≥1 | **Mandatory** |
| **6** | ≥2 | **Mandatory (v1.2 Patch F)** |

**Failure to meet D-minimum invalidates the weekly plan.**

**Reason Code:** `MCC_D_MINIMUM_VIOLATED`

---

## 4.5 Adjacency Sequencing Rules

### Forbidden Adjacency (Always Illegal)

| Pattern | Why Illegal | Consequence |
|---------|------------|-------------|
| **B→B (back-to-back)** | B limited to ≤1/week (3–5×) or buffered (6×) | Plan invalid |
| **A(BAND3)→B** | CNS fatigue + density work injury risk | Plan invalid |
| **3+ consecutive NODE 3 days** | Cumulative neural fatigue, rolling load cap | Plan invalid |

**Critical Correction (v1.1-K):** The "3 consecutive NODE 3 days" rule replaces the impossible "A at NODE 3" rule from earlier drafts. DAY A prohibits NODE 3, so that scenario cannot occur.

### 6× Exception (v1.2 Patch F)

**2 B days are allowed at 6× if:**
1. No B→B adjacency (e.g., Mon A / Tue D / Wed B / Thu C / Fri B / Sat D)
2. MCC Pass 2 validates: no forbidden patterns, density ledger GREEN/YELLOW, no 3+ consecutive NODE 3
3. MCC Pass 2 emits `MCC_ADJACENCY_VIOLATION` and/or `MCC_CONSECUTIVE_NODE3_EXCEEDED` on failure (and the weekly plan is rejected)

### Preferred Adjacency (Coaching Guidance)

| After This Day | Prefer Next Day | Rationale |
|----------------|-----------------|-----------|
| DAY A | C or D | Allow CNS recovery before density work |
| DAY B (NODE 3) | D or C (NODE 2) | Rotate density exposure |
| DAY C | A or B | Allow structural work to recover before heavy loading |
| DAY D | A or B | Recovery complete; ready for stimulus |

**Reason Codes (MCC Pass 2):** `MCC_ADJACENCY_VIOLATION`, `MCC_CONSECUTIVE_NODE3_EXCEEDED`

---

## 4.6 Weekly Pattern Balance Rule (Patch G-01, CORRECTED)

**Goal:** Prevent structurally imbalanced programs that are formally legal but biologically harmful.

### Pattern Distribution Method: Split-Counting for Dual-Tagged Exercises

Each working set is tagged with a primary push/pull value in ECA:
- **push** – Upper-body pressing, leg press, front-loaded movements
- **pull** – Upper-body pulling, posterior-chain dominant
- **mixed** – Carries, trunk, multi-planar demand
- **none** – Isolation work without clear push/pull bias

### Split-Counting Rule (CRITICAL CORRECTION v1.1-K)

- **Single-tagged sets (push OR pull):** count 1.0 toward their category
- **Dual-tagged sets** (e.g., leg press = push 0.5, lower-compound 0.5): count 0.5 toward each category, NOT 1.0 in both
- **Mixed/trunk/carry:** count 0 toward push/pull; tracked separately as structural work

**Why This Matters:** Prevents inflation. A leg press cannot count as both a full push AND a full lower-body primary; it contributes 0.5 to each to acknowledge its dual role without over-crediting.

### Weekly Pattern Balance Requirements

| Pattern Pair | Minimum Requirement | Condition |
|-------------|-------------------|-----------|
| **Push ↔ Pull** | 40% of WORK sets in each direction | OR 35% each if lower-body sets = 30% of weekly total |
| **Horizontal ↔ Vertical** | 35% of WORK sets in each plane | Applies to pressing and pulling work |
| **Primary ↔ Corrective** | 60% primary compound, 40% isolation/accessory | Across all days |
| **Frontal Plane** | 20% of WORK sets | Only required if frequency ≥5 |

### Example Calculation: 4-Day Week

**Weekly Structure:**
- DAY A: 8 push (bench, squat) + 4 pull (rows) = 8 push, 4 pull
- DAY B: 3 push + 3 pull isolation mix = 3 push, 3 pull
- DAY C-1: 2 push + 4 pull + 2 mixed (lower posterior focus) = 2 push, 4 pull, 2 mixed
- DAY C-2: 0 push + 4 pull + 1 mixed (upper posterior) = 0 push, 4 pull, 1 mixed

**Weekly Totals (Upper-Body Focus):**
- Push: 8+3+2+0 = 13 sets
- Pull: 4+3+4+4 = 15 sets
- Mixed/lower: 3 sets (not counted in push/pull ratio)
- Total upper-tracking: 13+15 = 28 sets

**Validation:**
- Push: 13/28 = 46% ✓ (exceeds 40% minimum)
- Pull: 15/28 = 54% ✓ (exceeds 40% minimum)
- Pattern balance: **PASS**

### Dual-Tag Split-Count Example

**Exercise:** Leg Press tagged as push: 0.5, lower-compound: 0.5
**Session:** 3 sets of leg press at BAND 2

**Counting:**
- Push category: 3 × 0.5 = 1.5 sets
- Lower-body primary category: 3 × 0.5 = 1.5 sets
- **NOT** 3 sets in each (which would be 6 total credits from 3 actual sets)

### Validation Rule

Weekly plan validator must compute pattern distribution using split-counting and flag if any pair falls below minimum threshold.

**Reason Code:** `MCC_PATTERN_BALANCE_VIOLATED`

---

## 4.7 Aggregate H-Node Density Cap (Patch F-02, CORRECTED)

### Problem

While H4 is strictly capped to 1 WORK block per week, H3 hybrid/density techniques carry substantial neural and local fatigue risk when scattered across multiple days—even if per-session rules are satisfied.

### H3 Session Definition

An **H3 session** is any training day in which ≥1 H3 archetype (from ECA Patch N-01) is used.

**H3 Archetypes:**
- Superset (antagonist muscles)
- Superset (same muscle group)
- Pre-exhaust (isolation→compound, same muscle)
- Density circuit (≥3 exercises, continuous rotation)
- Drop set (advanced)
- Myo-rep (mechanical drop set)
- Rest-pause
- Cluster set

### H3 Counting Rule

- **Weekly cap:** 3 H3 sessions per microcycle
- **Per-session limit:** Each H3 session can contain ≤2 distinct H3 archetypes

**Rationale:** Prevents cumulative neural fatigue and local tissue overuse while remaining within per-session legality.

### Example Scenario

| Day | H3 Behavior | H3 Session Count | Notes |
|-----|------------|-----------------|-------|
| DAY A | None | 0 | Heavy strength; no H3 |
| DAY B (Week 1) | 1 antagonist superset (bench ↔ row) | 1 | H3 session count = 1 |
| DAY C-1 | None | 1 | (unchanged) |
| DAY C-2 | 2 density circuits (leg press, shoulder) | 2 | H3 session count = 2 |
| **Weekly Total** | — | **2/3** | Within cap |
| DAY C-1 (Week 2 with H3 added) | Add H3 | 3 | Weekly total = 3/3 (at maximum) |
| DAY A (same week with H3) | Add H3 (illegal anyway) | 4 | **Weekly total = 4/3 (VIOLATED)** |

**Reason Code:** `MCC_H3_AGGREGATE_EXCEEDED`

---

## 4.8 Weekly Density Ledger (Patch F-01 + NODE 3 Permission Pre-Condition)

### Problem

BAND 2–NODE 3 combinations create near-maximal neural stress without triggering BAND 3 legality gates, enabling silent CNS overload.

### Pre-Condition for NODE 3 Counting (Patch P-01 Integration)

**Before applying density ledger thresholds, validate that all NODE 3 work uses exercises with ECA nodemax ≥3.**

**Validation Sequence:**
1. Identify all sets marked as NODE 3 in weekly plan
2. For each set, check exercise ECA entry: `nodemax ≥ 3`?
3. If any set fails → `MCC_NODE_PERMISSION_VIOLATION` (session invalid; do NOT proceed to ledger)
4. If all sets pass → Proceed to density ledger calculation

**This ensures density caps apply only to LEGAL NODE 3 usage.**

### Density Ledger Thresholds

| Density Metric | Green Zone | Yellow Zone | Red Zone |
|---|---|---|---|
| **Total NODE 3 sets/week (all bands)** | ≤40 sets | 41–60 sets | ≥60 sets |
| **BAND 2 + NODE 3 sets/week** | ≤20 sets | 21–30 sets | ≥30 sets |

### Action by Zone

- **Green:** Proceed as normal; no intervention required
- **Yellow:** Coach awareness flag; monitor readiness closely next session; consider intensity reduction if readiness degrades
- **Red:** Weekly plan invalid; reduce NODE 3 volume or redistribute across different nodes

**Reason Codes:** `MCC_DENSITY_LEDGER_EXCEEDED`, `MCC_NODE_PERMISSION_VIOLATION`

---

# 5. SESSION STRUCTURE (from DCC v2.2)

All sessions follow the 4-block structure inherited from DCC v2.2:

| Block | Time Range | Purpose | RPE Cap | Notes |
|-------|-----------|---------|---------|-------|
| **PRIME** | 8–10 min | Global warm-up; joint prep; tissue readiness | 3 | Movement prep specific to WORK demands |
| **PREP** | 10–12 min | Movement rehearsal; activation at BAND 0–1; ramp sets | 3 | Pattern-specific preparation |
| **WORK** | 24–30 min | **Primary training stimulus** | Varies | Minimum 24 min required; maximum 30 min (all day roles) |
| **CLEAR** | 5–8 min | Cooldown; parasympathetic shift; mobility; recovery initiation | 2 | Breathing protocols, stretching |

### Session Duration Hard Caps

| Metric | Limit | Reason |
|--------|-------|--------|
| **Total session** | 50–60 min | Prevents session creep |
| **WORK block minimum** | 24 min | Ensures sufficient stimulus |
| **WORK block maximum** | 30 min | Prevents junk volume and silent fatigue accumulation |

**Reason Codes:** `MCC_SESSION_DURATION_EXCEEDED`, `MCC_WORK_BLOCK_INSUFFICIENT`

---

# 6. TRAINING ROUTES FOR HYPERTROPHY

Training routes define stimulus intent and termination criteria, not just exercise selection.

## 6.1 Route: MAX_STRENGTH_EXPRESSION

| Parameter | Specification |
|-----------|---------------|
| **Intent** | Peak mechanical tension; maximal force production; 1–5 reps |
| **Band/Node** | BAND 3, NODE 1 |
| **H-Node** | H1 only |
| **Termination** | Output drop ≥10% or bar speed decay |
| **Readiness Gate** | GREEN only |
| **Frequency** | Primary on DAY A |

---

## 6.2 Route: SUBMAX_HYPERTROPHY_VOLUME

| Parameter | Specification |
|-----------|---------------|
| **Intent** | Volume-load optimization; primary hypertrophy zone; 6–12 reps |
| **Band/Node** | BAND 2, NODE 2 |
| **H-Node** | H1–H2 |
| **Termination** | Technical failure (not muscular failure); maintain bar speed |
| **Frequency** | Primary on DAY A and DAY B |

---

## 6.3 Route: CAPACITY_ACCUMULATION

| Parameter | Specification |
|-----------|---------------|
| **Intent** | Metabolic stress; work capacity; time-under-tension; 12–20+ reps |
| **Band/Node** | BAND 1–2, NODE 2–3 |
| **H-Node** | H2–H3 |
| **Termination** | Planned volume completion or time cap |
| **Frequency** | Primary on DAY B and DAY C |

---

## 6.4 Route: REGENERATION

| Parameter | Specification |
|-----------|---------------|
| **Intent** | Active recovery; movement quality; tissue health |
| **Band/Node** | BAND 0–1, NODE 1 |
| **H-Node** | H0–H1 |
| **Termination** | Time-based; no performance goal |
| **Frequency** | DAY D or readiness-driven override (YELLOW/RED collapse) |

---

# 7. READINESS SYSTEM FOR PHYSIQUE TRAINING

## 7.1 Readiness Inputs (Weighted Authority)

| Input | Scale | Weight | Notes |
|-------|-------|--------|-------|
| **Joint pain/discomfort** | 0–10 | PRIMARY | Non-negotiable; ≥5 = RED |
| **Muscle soreness** | Acute vs DOMS | PRIMARY | Distinguish injury pain from training adaptation |
| **Sleep quality** | Hours + subjective (0–10) | SECONDARY | <5h or quality <4 = concern |
| **Training stress balance** | 7-day rolling | SECONDARY | Cumulative load assessment |
| **Performance markers** | RIR deviation, bar speed | CONTEXT | Validates subjective inputs |

---

## 7.2 Readiness States

### GREEN (Full Envelope)

- **Pain:** 0–2 (minimal, localized only)
- **Soreness:** DOMS only, no acute strain
- **Sleep:** ≥7h, quality ≥7/10
- **Performance:** At or above baseline
- **Action:** Execute planned session; all routes available; BAND 3 permitted

---

### YELLOW (Downgrade Required)

- **Pain:** 3–4 (noticeable but not limiting)
- **Soreness:** Systemic or lingering beyond typical DOMS
- **Sleep:** 5–6.5h or quality 4–6/10
- **Performance:** ~10% below baseline (RIR deviation, bar speed drop)
- **Action:**
  - **Intensity reduction:** Reduce BAND ceiling by 1 (BAND 3→BAND 2; BAND 2→BAND 1)
  - **Volume reduction:** Apply multiplier **0.8×** to planned working sets
  - **Both applied simultaneously** (CRITICAL CORRECTION from v1.1-K Patch I-03)
  - **BAND 3 prohibited** at YELLOW readiness

**Rationale:** YELLOW requires both intensity AND volume modulation to prevent disguised overload.

---

### RED (Collapse)

- **Pain:** ≥5 (sharp, joint-specific, limiting)
- **Severe fatigue markers:** Dizziness, nausea, systemic exhaustion
- **Sleep:** <5h or quality <3/10 with other compounding factors
- **Action:**
  - Collapse to BAND 0–1, H0–H1 only (active recovery)
  - Apply volume multiplier **0.5×** OR full rest day
  - Medical review recommended if pain-driven

---

## 7.3 Chronic YELLOW Guard (Patch I-01)

**Trigger:** Athlete/coach records YELLOW or RED readiness on ≥3 out of 7 consecutive days.

**Action (Mandatory):**
1. **Forced check-in** required before next session
2. Medical/coach review of readiness inputs (sleep, stress, nutrition, illness)
3. If no acute cause identified → **mandatory volume/intensity reduction or unload day**
4. If pattern continues (≥3 YELLOW in rolling 7-day window for 2+ weeks) → escalate to medical hold or mesocycle reset

**Purpose:** Prevents chronic fatigue tolerance and progressive degradation masked by formal session legality.

**Reason Code:** `MCC_CHRONIC_YELLOW_GUARD_TRIGGERED`

---

# 8. VOLUME LANDMARKS & CLASSIFICATION (CORRECTED v1.1-K)

## 8.1 Weekly Volume Landmarks (WORK Sets Only)

Volume measured in **working sets only** (excludes warm-ups, ramp sets, PREP block activation).

| Muscle Group Type | Sets / Week | Examples |
|-------------------|------------|----------|
| **Major** | 10–20 | Quads, back (lats), chest |
| **Minor** | 8–16 | Biceps, triceps, delts, calves |
| **Postural / stability** | 6–12 | Rear delts, rotator cuff, glutes, hamstrings (when trained as secondary) |

**Note:** Some muscles (e.g., glutes, hamstrings) may shift between categories depending on training phase and exercise selection.

---

## 8.2 Material Load Classification Test (Patch G-02 + M-01)

When assigning `volume_class` in ECA, use this **deterministic decision tree**:

### PRIMARY (1.0× toward landmark)

Exercise is a **prime mover** for the target muscle:
- **AND** exercise is loaded ≥50% of target muscle's estimated 1RM
- **AND** movement_family ∈ {squat, hinge, press, pull}

**Examples:**
- Barbell squat (quad primary)
- Bench press (chest primary)
- Barbell row (back primary)
- Deadlift (posterior chain primary)

---

### ASSISTANCE (0.5× toward landmark)

Exercise supports a primary pattern but is **secondary load**:
- **OR** loaded 25–50% of target muscle's estimated 1RM
- **OR** is a unilateral variant of a primary pattern (split squat, single-arm row)
- **OR** is a machine/modified version of a primary (leg press, machine chest press)

**Examples:**
- Incline DB press (chest secondary/assistance)
- Split squat (quad secondary/assistance)
- Leg press (quad assistance, despite heavy load—due to stability reduction)
- Single-arm DB row (back assistance)

---

### ACCESSORY (0.25× toward landmark)

Exercise is **isolation or corrective**:
- **AND** movement_family ∈ {isolate, trunk}
- **AND** loaded ≤25% of target muscle's estimated 1RM

**Examples:**
- Face pulls (rear delt isolation)
- Tricep pushdown (tricep isolation)
- Cable curl (bicep isolation)
- Leg curl (hamstring isolation)

---

### Special Case: Multi-Muscle Loaded Carries

Farmer carry, suitcase carry, front-loaded carry, overhead carry:
- **Classified as ASSISTANCE** for all loaded muscles (grip, trunk, shoulders, legs)
- **NOT ACCESSORY** despite distributed load
- **Rationale:** Meaningful load across multiple regions contributes to structural integrity

---

## 8.3 Enforcement (Patch M-01): Volume Class Immutability

`volume_class` is **read-only from ECA** in compliant implementations.

**Rules:**
- Coaches cannot override Primary ↔ Assistance ↔ Accessory classification at program level
- Classification is assigned once in ECA and is **immutable across all programs**
- Legacy label `VOLUMECLASSIMMUTABILITYVIOLATED` is governed as the same condition; canonical emitted code is `MCC_VOLUME_CLASS_OVERRIDE_ATTEMPT`
- Any override attempt → `MCC_VOLUME_CLASS_OVERRIDE_ATTEMPT`

**Example:** If hip thrust is classified as Primary for glutes in ECA, it cannot be reclassified as Assistance in a different program to inflate volume without reaching landmark ceilings.

**Reason Code:** `MCC_VOLUME_CLASS_OVERRIDE_ATTEMPT`

---

# 9. PROGRESSIVE OVERLOAD LOGIC (EPA BINDING)

From EPA Exercise Progression Law v1.0.2, adapted for physique training.

## 9.1 Progression Axis Priority for Hypertrophy

| Axis | Definition | Typical Application |
|------|-----------|-------------------|
| **1. Volume** | Sets / reps | Increase total working reps or sets per session/week |
| **2. Load** | Weight on bar (% 1RM) | Increase absolute load for same rep range |
| **3. Density** | Rest periods | Shorten inter-set rest; increase reps/min |
| **4. Complexity** | H-Node progression | H1→H2, H2→H3, H3→H4 (under weekly caps) |

---

## 9.2 ONE AXIS AT A TIME Rule (Non-Negotiable)

**Per microcycle (weekly):**
- Progress **one axis only** per exercise or movement pattern
- Do NOT increase volume + load simultaneously (e.g., 3×10@100lb → 4×12@110lb in same week)
- Do NOT increase load + density simultaneously (e.g., 80lb@3min rest → 85lb@2min rest in same week)
- Do NOT progress H-Node level ×1 per mesocycle (4-week block)

**Known Limitation:** Deferred to tooling. Without a persistent progression ledger, coaches can accidentally stack axes via different exercises in the same week (e.g., progress squat volume + deadlift load in same microcycle). Current mitigation: narrative rule + coaching discipline. Future tooling will enforce via exercise-level progression tracking (ECA Patch H, deferred).

**Reason Code:** `MCC_MULTI_AXIS_PROGRESSION_VIOLATION`

---

# 10. MESOCYCLE STRUCTURE & REACTIVE DELOAD (v1.1 HARDENED)

## 10.1 Default Mesocycle Length

- **1 mesocycle = 4 weeks (4 microcycles)**

---

## 10.2 Week 4: Mandatory Deload

**Every mesocycle concludes with a planned deload week:**
- **Volume reduction:** 25–40% of planned working sets
- **Intensity maintenance:** BAND ceilings unchanged (unless readiness forces further downgrade)
- **No axis progression allowed** during Week 4
- **Readiness reassessment** before next mesocycle begins

---

## 10.3 Reactive Deload Triggers (Patch E-04)

In addition to fixed Week 4 deload, a **reactive deload is mandatory** if any of the following occur:

| Trigger | Definition | Action |
|---------|-----------|--------|
| **Collapse Pattern** | ≥2 session collapses in 7 days | Immediate deload |
| **Chronic YELLOW** | ≥3 YELLOW/RED days in 7-day rolling window | Forced intervention; deload if unresolved (Section 7.3) |
| **Route Saturation** | MAX_STRENGTH_EXPRESSION attempted >1 DAY A in same mesocycle | Signals inappropriate density; trigger deload |
| **Performance Plateau** | ≥2 consecutive weeks with no progression on any axis AND readiness YELLOW/RED | Reactive deload |

---

## 10.4 Reactive Deload Mechanics

**When triggered:**
- Current meso week becomes **immediate deload** (40% volume, collapse to BAND 0–1 or BAND 1–2 only)
- Following week resumes normal progression; meso continues
- No mesocycle skip required; reactive deload costs 1 week but resets accumulated fatigue
- If reactive deload occurs in Week 4, **combine with planned deload** (do NOT double-deload)

**Reason Code:** `REACTIVEDELOADTRIGGERED`

---

# 11. SESSION ABORT PROTOCOL (HYPERTROPHY CONTEXT)

## 11.1 Collapse-to-CLEAR Triggers

**Immediately abort WORK block and shift to CLEAR if any of the following occur:**

| Trigger | Response |
|---------|----------|
| **Joint pain escalates ≥3 points during session** | Stop WORK; shift to CLEAR |
| **Form breakdown cannot be restored after 1 full rest period** | Stop exercise; assess alternative or abort |
| **Bar speed drops ≥10% from baseline on compound lift across multiple sets** | Stop pattern; shift to lower-intensity alternative or CLEAR |
| **Strain or sharp localized pain (non-DOMS)** | Stop exercise; medical review if persists |
| **Dizziness, nausea, acute distress** | Immediate stop; CLEAR or full rest |

---

## 11.2 Immediate Actions on Collapse

1. Stop current exercise/block immediately
2. Shift to CLEAR block (mobility, light movement, downregulation)
3. Log trigger and mark session as COLLAPSED
4. Do NOT make up missed volume later in day or week (prevents disguised overload)
5. Reassess readiness before next scheduled session

---

## 11.3 Forced Meso Intervention (Patch I-02)

**If ≥2 collapses in 7 days OR ≥3 collapses in 14 days:**
1. Immediate mandatory medical/coach review
2. Action:
   - (a) Forced unload day + readiness re-assessment, OR
   - (b) Full mesocycle reset if pattern persists
3. Documentation: Log collapse trigger, session state at abort, response action

**Purpose:** Prevents tolerance to session failure; escalates intervention before chronic injury.

**Reason Code:** `MCC_COLLAPSE_ESCALATION_TRIGGERED`

---

# 12. PRIME BINDING FOR PHYSIQUE TRAINING

PRIME is inherited from DCC v2.2 with strict scope enforcement.

## 12.1 PRIME Selection Logic

1. Declare Day Role (A/B/C/D) **before** selecting PRIME content
2. Identify primary movement patterns in WORK block
3. Select PRIME content to prepare those patterns (joint-specific, tissue-specific, nervous system priming)
4. PRIME must rotate (anti-repetition rule; Section 12.3)

---

## 12.2 PRIME Scope Lock

### What PRIME Is (Always Legal)

- Movement preparation for WORK demands (e.g., hip flexor stretch before squats)
- Joint preparation for primary patterns in WORK (e.g., shoulder dislocates before pressing)
- Low-level tissue readiness (8–10 min at RPE ≤3)
- Nervous system priming (e.g., light jumping, medicine ball throws at BAND 0)

### What PRIME Is NOT (Always Illegal)

- Activation circuits dosed at meaningful volume (those belong in WORK if loaded)
- Conditioning sequences or repeated efforts that drive fatigue
- Formal breathing protocols (those belong in CLEAR)
- Any drill that raises HR significantly, causes fatigue, or is dosed at meaningful volume

### Legality Test

**If a drill raises HR significantly, causes fatigue, or is dosed at meaningful volume → ILLEGAL PRIME content.**

**Reason Code:** `MCC_PRIME_SCOPE_VIOLATION`

---

## 12.3 PRIME Anti-Repetition Rule

**Rule:** PRIME content should not repeat identically across consecutive sessions.

**Purpose:** Prevents neural habituation and silent adaptation plateau.

**Known Limitation:** Deferred to tooling. Without persistent storage of PRIME history, this rule is not machine-enforceable in v1.2. Current mitigation: coaching discipline + manual rotation.

**Reason Code (Warning Only):** `PRIMEREPETITIONWARNING`

---

# 13. ALWAYS-ILLEGAL BEHAVIORS (COMPREHENSIVE TABLE, v1.2.1)

| Behavior | Why Illegal | Consequence | Reason Code |
|----------|-----------|-------------|-----------|
| **BAND 3 + NODE 3 simultaneous** | CNS overload + metabolic fatigue = injury risk | Session invalid; downgrade to BAND 2–NODE 2 or BAND 3–NODE 1 | `MCC_BAND_NODE_ILLEGAL_COMBINATION` |
| **>25 working sets in session** | Junk volume, diminishing returns, silent fatigue | Session invalid; cap at 25 sets | `MCC_SESSION_VOLUME_EXCEEDED` |
| **>1 movement pattern at BAND 3 per session** | Hidden CNS overload across patterns | Session invalid; limit BAND 3 to 1 pattern | `MCC_BAND3_PATTERN_EXCEEDED` |
| **DAY A with <3 compound lifts** | Violates primary strength guarantee | Session invalid; restructure | `MCC_DAY_A_PATTERN_GUARANTEE_VIOLATED` |
| **RED readiness + full load** | Ignores recovery debt = injury risk | Session invalid; collapse to BAND 0–1 or rest day | `MCC_READINESS_VIOLATION` |
| **YELLOW readiness + BAND 3** | Insufficient recovery for maximal loads | Session invalid; cap at BAND 2 | `MCC_READINESS_BAND_MISMATCH` |
| **Session >60 min total** | Silent fatigue accumulation, adherence risk | Session invalid; reduce WORK duration or exercise count | `MCC_SESSION_DURATION_EXCEEDED` |
| **WORK block <24 min** | Insufficient stimulus | Session invalid; extend WORK or add exercises | `MCC_WORK_BLOCK_INSUFFICIENT` |
| **2-axis progression in same week** | Violates ONEAXIS rule (EPA binding) | Progression invalid; revert 1 axis | `MCC_MULTI_AXIS_PROGRESSION_VIOLATION` |
| **Family-level multi-axis progression** | E.g., squat volume + deadlift load same week | Progression flagged (coaching mitigation; future tooling enforces) | `MCC_FAMILY_MULTI_AXIS_VIOLATION` |
| **>1 H4 block per week** | Peak CNS stress over-exposure | Weekly plan invalid; remove H4 or defer | `MCC_H4_FREQUENCY_EXCEEDED` |
| **>3 H3 sessions per week** | Neural + local fatigue accumulation | Weekly plan invalid; redistribute H3 or remove | `MCC_H3_AGGREGATE_EXCEEDED` |
| **NODE 3 on non-approved exercise** | Permission violation (Patch P-01) | Session invalid before ledger calculation | `MCC_NODE_PERMISSION_VIOLATION` |
| **BAND 2–NODE 3 >30 sets/week** | Near-maximal stress without BAND 3 legality | Weekly plan flagged YELLOW (21–30) or invalid (≥30) | `MCC_DENSITY_LEDGER_EXCEEDED` |
| **Total NODE 3 >60 sets/week** | Chronic density overload | Weekly plan invalid; reduce NODE 3 volume | `MCC_DENSITY_LEDGER_EXCEEDED` |
| **Pattern balance violated** | Structural imbalance = postural dysfunction, asymmetry | Weekly plan invalid; redistribute patterns | `MCC_PATTERN_BALANCE_VIOLATED` |
| **DAY D exercise not on whitelist** | Intent violation (Patch O-01) | Session invalid; remove non-whitelisted exercises | `MCC_DAY_D_INTENT_VIOLATION` |
| **DAY C pattern repeats in consecutive weeks** | Local tissue abuse = overuse without variety | Weekly plan invalid; rotate C-day tissue targets | `MCC_DAY_C_PATTERN_REPETITION` |
| **Identical PRIME content 2+ sessions** | Neural habituation = adaptation plateau | Warning only (coaching discipline required) | `PRIMEREPETITIONWARNING` |
| **PRIME with activation circuits/conditioning** | Scope creep = fatigue generation | Session invalid; move content to WORK or remove | `MCC_PRIME_SCOPE_VIOLATION` |
| **Frequency not in {3, 4, 5, 6}** | Undefined deployment rules | Weekly plan invalid | `MCC_FREQUENCY_NOT_SUPPORTED` |
| **DAY A >1 per week** | CNS overload | Weekly plan invalid | `MCC_DAY_A_FREQUENCY_EXCEEDED` |
| **DAY B >1 per week (at 3–5×/week)** | Density saturation | Weekly plan invalid | `MCC_DAY_B_FREQUENCY_EXCEEDED` |
| **DAY B >2 per week (at 6×/week)** | Exceeds Patch F exception ceiling | Weekly plan invalid | `MCC_DAY_B_FREQUENCY_EXCEEDED` |
| **5×/week without ≥1 DAY D** | Missing mandatory recovery | Weekly plan invalid | `MCC_D_MINIMUM_VIOLATED` |
| **6×/week without ≥2 DAY D** | **v1.2 Patch F mandatory** | Weekly plan invalid | `MCC_D_MINIMUM_VIOLATED` |
| **Forbidden adjacency (B→B, A(BAND3)→B, 3+ consecutive NODE 3)** | CNS/density stacking without recovery | Weekly plan invalid | `MCC_ADJACENCY_VIOLATION`, `MCC_CONSECUTIVE_NODE3_EXCEEDED` |
| **Exercise not in ECA** | Ungoverned movement = undefined classification | Session invalid; add to ECA before use | `MCC_ECA_COVERAGE_MISSING` |
| **Exercise missing pattern tuple** | Cannot validate pattern balance | Session invalid; complete ECA tagging | `MCC_ECA_PATTERN_INCOMPLETE` |
| **Volume class override attempt** | Immutability violation (Patch M-01) | Override rejected; use ECA classification | `MCC_VOLUME_CLASS_OVERRIDE_ATTEMPT` |
| **≥2 collapses in 7 days without escalation** | Tolerance to session failure | Forced meso intervention | `MCC_COLLAPSE_ESCALATION_TRIGGERED` |
| **≥3 YELLOW/RED days in 7-day window (ignored)** | Chronic YELLOW accumulation = silent fatigue | Forced check-in + intervention | `MCC_CHRONIC_YELLOW_GUARD_TRIGGERED` |

---

# 14. ECA ENFORCEMENT PATCHES (GROUPS K–P): MANDATORY FOR v1.2.1 COMPLIANCE

DCC-Physique v1.2.1 philosophy: Sections 1–13 define the training law. **Patches K–P represent the mandatory implementation layer** that makes all rules auditable, deterministic, and exploit-proof.

**Without K–P:** v1.2.1 remains principle-based.  
**With K–P:** v1.2.1 becomes fully specification-enforceable.

### Patch Group K: Exclusive Coverage Rule

**Problem:** Exercises not listed in ECA create ungoverned zones. Coaches can use unlisted movements, apply freeform tags, or claim "similar enough" to bypass volume controls, pattern balance, and density caps.

#### K-01 Exclusive Exercise Authority

**Only exercises explicitly present in the ECA exercise master list are legal for DCC-Physique session construction.**

**Rules:**
- Any exercise NOT in ECA → `MCC_ECA_COVERAGE_MISSING` (session invalid)
- No free-text exercise entry in compliant implementations
- No inference (e.g., "treat this DB variation like the barbell version")
- Unlisted movements must be added to ECA with complete tagging before use

**Enforcement Point:** Session validator checks all WORK block exercises against ECA master list before proceeding to any other validation rules.

---

#### K-02 Required Expansion Domains

The following movement families **must have complete ECA coverage** to support common physique training needs:

| Domain | Examples | Minimum Coverage |
|--------|----------|------------------|
| **Machine Presses (Horizontal)** | Chest machine, lever press, Smith horizontal | 3 variants |
| **Machine Presses (Vertical)** | Shoulder press machine, lever overhead press | 3 variants |
| **Machine Rows (Horizontal)** | Chest-supported row, leverage row, cable row | 3 variants |
| **Machine Rows (Vertical)** | Lat pulldown machine, assisted pull-up, high-cable row | 3 variants |
| **Curl Archetypes** | Barbell, DB, cable, machine, EZ-bar, Smith, preacher | 6 variants |
| **Extension Archetypes** | Pushdown, skull crusher, overhead extension, machine, dips | 5 variants |
| **Hip Abduction/Adduction** | Machine, cable, band, lateral lunge, Copenhagen plank | 4 variants |
| **Leg Curl Family** | Lying, seated, standing, machine, Nordic | 4 variants |
| **Leg Extension Family** | Machine, single-leg, lever, Spanish squat | 3 variants |
| **Calf Raises** | Standing, seated, machine, single-leg, Smith | 4 variants |
| **Selectorized Machines** | Hammer Strength, plate-loaded, cable stations | Full parity with barbell/DB equivalents |

**Rationale:** These domains represent common physique training exercises that must be governed to prevent "I didn't know it needed to be classified" loopholes.

**Compliance Check:** ECA must demonstrate coverage in all domains before system goes operational.

---

### Patch Group L: Pattern-Balance Tag Completeness

**Problem:** Section 4.6 Weekly Pattern Balance Rule requires `push_pull`, `horiz_vert`, and `movement_family` tags for every exercise. If any field is missing or ambiguous, weekly validation fails silently or defaults incorrectly, allowing structurally imbalanced programs to pass.

#### L-01 Mandatory Pattern Tuple

**Every ECA exercise row must include a complete pattern tuple:**

| Field | Valid Values | Purpose | Example |
|-------|-------------|---------|---------|
| **push_pull** | push, pull, mixed, none | Upper-body force direction or multi-directional demand | Bench = push; Row = pull; Leg Press = mixed; Plank = none |
| **horiz_vert** | horizontal, vertical, sagittal, frontal | Primary plane of motion for pattern balance | Bench (horizontal); Overhead press (vertical); Leg press (sagittal) |
| **movement_family** | squat, hinge, press, pull, carry, isolate, trunk | Movement archetype | Squat (squat); Deadlift (hinge); Curl (isolate); Plank (trunk) |

**Missing any field → `MCC_ECA_PATTERN_INCOMPLETE` (exercise cannot be used). No defaults allowed. Every exercise must be explicitly classified.**

**Runtime Boundary Clarification (Whitelist/ECA → MCC):** Law-level runtime `horiz_vert` taxonomy for pattern-balance enforcement remains `horizontal|vertical|sagittal|frontal`. Whitelist/ECA authoring may retain richer labels (e.g., `Incline`) but those labels are not injected directly into MCC schema fields; runtime must apply an explicit, deterministic normalization adapter before MCC validation. If no mapping is defined, validation fails closed (no implicit collapse/defaulting).

---

#### L-02 Dual-Tagged Exercises: Explicit Split-Counting

**Exercises spanning two roles must be explicitly dual-tagged in ECA with split-counting coefficients:**

| Exercise | Dual Tag | Split-Count Rule | Rationale |
|----------|----------|------------------|-----------|
| **Leg Press** | push: 0.5, lower-compound: 0.5 | 3 sets → 1.5 push + 1.5 lower-compound | Front-loaded; contributes to both push pattern and leg development |
| **Chest-Supported Row** | pull: 1.0, horizontal: 1.0 | 3 sets → 3 pull + 3 horizontal | Pure horizontal pull; counts fully in both axes |
| **Bulgarian Split Squat** | squat: 0.7, frontal: 0.3 | 3 sets → 2.1 squat + 0.9 frontal | Primary squat pattern with frontal stability demand |
| **Farmer Carry** | carry: 1.0, mixed: 1.0 | Tagged as ASSISTANCE for grip, trunk, shoulders, legs | Multi-muscle loaded; meaningful load across regions |

---

### Patch Group M: Volume Class Immutability

**Problem:** Coaches could override `volume_class` (PRIMARY, ASSISTANCE, ACCESSORY) at program level to inflate or deflate volume counts without hitting landmark ceilings.

#### M-01 Read-Only Classification

`volume_class` is **read-only from ECA** in compliant implementations.

**Rules:**
- Coaches cannot override PRIMARY ↔ ASSISTANCE ↔ ACCESSORY at program level
- Classification is assigned once in ECA and is **immutable across all programs**
- Legacy label `VOLUMECLASSIMMUTABILITYVIOLATED` is governed as the same condition; canonical emitted code is `MCC_VOLUME_CLASS_OVERRIDE_ATTEMPT`
- Any override attempt → `MCC_VOLUME_CLASS_OVERRIDE_ATTEMPT`

**Example:** If hip thrust is classified as PRIMARY for glutes in ECA, it cannot be reclassified as ASSISTANCE in a different program to inflate volume without reaching landmark ceilings.

---

### Patch Group N: H-Node Archetype Taxonomy

**Problem:** Without explicit H-node archetype definitions, coaches interpret "H3" or "advanced technique" differently, enabling scope creep and hidden neural overload.

#### N-01 Mandatory H-Node Archetype Tags

Every exercise using H3 or H4 must be tagged with a specific archetype:

| H-Node Archetype | Definition | Neural Load | Example |
|-----------------|-----------|------------|---------|
| **Superset (antagonist)** | 2 exercises, opposite muscle groups, minimal rest | High | Bench ↔ Rows in alternation |
| **Superset (same muscle)** | 2 exercises, same muscle group, minimal rest | Very High | DB Press + Push-ups |
| **Pre-exhaust** | Isolation→Compound, same muscle, continuous | High | Leg curls→Squats |
| **Density circuit** | ≥3 exercises, continuous rotation, time-capped | High | Leg press→Leg curl→Hip thrust (4 min) |
| **Drop set (advanced)** | Pyramid down in load, continuous reps | High | 100lb×5 → 80lb×5 → 60lb×8 |
| **Myo-rep (mechanical drop)** | Load reduction via ROM restriction, continuous | High | Full ROM squats → Quarter squats |
| **Rest-pause** | Set to RPE 8–9, micro-rest (10–20 sec), resume | Very High | Bench 10 reps (RPE 8) + rest 15 sec + 5 more |
| **Cluster set** | Mini-sets with short inter-set rest (30–60 sec) | High | 3×3 deadlifts, 45 sec rest between |

---

### Patch Group O: Day-Role Whitelist Enforcement

**Problem:** DAY C and DAY D require specific intent (structural balance vs pure recovery). Without whitelist enforcement, coaches slip in loaded work disguised as "structural."

#### O-01 Whitelist Enforcement

**Only exercises with `day_roles_allowed` containing the target day role in ECA are legal:**

- **DAY A whitelist:** Compound patterns (squat, hinge, press, pull) with high loading tolerance; no isolation
- **DAY B whitelist:** Hypertrophy patterns (isolation, unilateral, supersets allowed); load and volume bias
- **DAY C whitelist:** Structural/corrective focus; posterior chain, rotator cuff, unilateral stability, trunk anti-rotation
- **DAY D whitelist:** True recovery; mobility, low-load tissue quality, band work, light machines; NO near-failure sets

**Validation:** Session validator checks each exercise's `day_roles_allowed` array against the declared day role.

**Violation Code:** `MCC_DAY_D_INTENT_VIOLATION`, `MCC_ECA_COVERAGE_MISSING`, `MCC_ECA_PATTERN_INCOMPLETE`

---

### Patch Group P: NODE 3 Opt-In Permission Gate

**Problem:** Without explicit opt-in, coaches use NODE 3 (high density) on unstable or injury-prone movements, creating silent CNS overload without triggering BAND 3 legality gates.

#### P-01 NODE 3 Permission Rule (CRITICAL)

**NODE 3 is opt-in only via ECA `nodemax` field.**

**Rules:**
- **Default:** `nodemax ≤ 2` → NODE 3 illegal
- **Permitted:** Only exercises with explicit `nodemax ≥ 3` in ECA may be used at NODE 3
- **Validation:** Before counting NODE 3 sets toward density ledger, validate permission
- **Violation:** `MCC_NODE_PERMISSION_VIOLATION` (session invalid)

**Pre-Condition for Density Ledger (Section 4.8):**
1. Identify all sets marked as NODE 3
2. For each, check ECA `nodemax ≥ 3`?
3. If any set fails → `MCC_NODE_PERMISSION_VIOLATION` (do NOT proceed to ledger)
4. If all pass → Proceed to density ledger calculation

---

# 15. APPENDIX: v1.2.1 PATCH F FREQUENCY HARDENING SUMMARY

## F-01 6× Frequency Contract (v1.2)

**v1.2 introduces Patch F to align DCC-Physique with Program Framework v2.1, enabling safe 6×/week programs with MCC oversight.**

### What Changed from v1.1-K

| Aspect | v1.1-K | v1.2 (Patch F) |
|--------|--------|---------------|
| **DAY B cap at 6×** | 1 per week (absolute) | ≤2 per week (with MCC adjacency + density enforcement) |
| **6× Allocation** | A1, B1, C2–3, D2 | A1, B≤2, C1, D≥2 |
| **DAY D minimum at 6×** | Optional mention | **Mandatory (≥2 required)** |
| **Adjacency enforcement** | DCC (framework aware only) | **MCC Pass 2 enforces (no B→B, no A(BAND3)→B, etc.)** |
| **Density ledger** | Node-level caps | **BAND 2–NODE 3 also capped per MCC schema** |
| **Reason codes** | Standard set | Added `MCC_DAY_B_FREQUENCY_EXCEEDED` (6× exception if MCC pass) |

---

## F-02 MCC Integration (v1.2 Patch F)

**Patch F is fully enforced by MCC v1.0.1 schema and Pass 2 validation:**

- MCC `context.frequencyperweek = 6` → enables DAY B ≤2 composition
- MCC `routehistory`, `cdayfocushistory` track route saturation and C-day rotation
- MCC `Pass 2` validates adjacency (no forbidden patterns), density ledger (GREEN/YELLOW), and family-level axis locking
- MCC `EXPOSURE_LEDGER` tracks rolling 7/14/28-day NODE 3 and BAND 2–NODE 3 usage

**Result:** 6×/week programs are safe and auditable under joint DCC v1.2 + MCC v1.0.1 governance.

---

## F-03 Compliance Checklist for 6× Programs

Before committing a 6×/week program:

- [ ] Frequency = 6, day-role composition = A1, B≤2, C1, D≥2
- [ ] No B→B adjacency (MCC validates)
- [ ] No A(BAND3)→B adjacency (MCC validates)
- [ ] No 3+ consecutive NODE 3 days (MCC validates)
- [ ] Density ledger: BAND 2–NODE 3 ≤20 sets/week; total NODE 3 ≤40 sets/week (GREEN zone)
- [ ] Pattern balance: push/pull 40% each, horizontal/vertical 35% each, primary/corrective 60/40
- [ ] Readiness GREEN or controlled YELLOW (no RED)
- [ ] DAY D sessions ≥2 (mandatory at 6×)
- [ ] C-day tissue focus rotates across meso (no repeat >2 weeks)
- [ ] Route saturation: MAX_STRENGTH_EXPRESSION ≤1 per meso (not every week)

---


## F-04 Enforcement Handshake (DCC Pass 1 ↔ MCC Pass 2)

Patch F introduces a **conditional legality** case that must be enforced deterministically by the runtime shell.

### Pass Order (Mandatory)

1. **DCC Pass 1 (Weekly Composition & Local Session Legality)**
   - Validate `frequency_per_week ∈ {3,4,5,6}`.
   - Validate `DAY_A_count == 1`.
   - Validate `DAY_D_count` meets D-minimum (Section 4.4).
   - Validate `DAY_B_count`:
     - If `frequency_per_week ∈ {3,4,5}` → require `DAY_B_count ≤ 1`.
     - If `frequency_per_week == 6` → allow `DAY_B_count ≤ 2`.
   - If `frequency_per_week == 6` AND `DAY_B_count == 2` → emit **advisory flag**: `MCC_PASS2_REQUIRED_FOR_B2` and continue.

2. **MCC Pass 2 (Adjacency + Density Gates, Required when B2 or high-density exposure exists)**
   - Required when any of the following is true:
     - `frequency_per_week == 6 AND DAY_B_count == 2`
     - any `NODE 3` exposure exists (because ledger gating is authoritative)
     - long-horizon checks are requested (route saturation, C-day focus rotation)
   - MCC Pass 2 MUST validate:
     - **Forbidden adjacency** (Section 4.5): no B→B; no A(BAND3)→B; no 3+ consecutive NODE 3 days
     - **Weekly density ledger** (Section 4.8): GREEN/YELLOW allowed; RED invalid
     - **NODE 3 permission pre-condition** (Patch P-01 integration)
   - If MCC Pass 2 fails any gate, the weekly plan is rejected and must surface MCC reason codes (e.g., `MCC_ADJACENCY_VIOLATION`, `MCC_CONSECUTIVE_NODE3_EXCEEDED`, `MCC_DENSITY_LEDGER_EXCEEDED`, `MCC_NODE_PERMISSION_VIOLATION`).

### Deterministic Rejection Rule (Non-Negotiable)

If `frequency_per_week == 6` AND `DAY_B_count == 2` AND MCC Pass 2 is not executed or does not return PASS, the weekly plan is **invalid** (do not “assume safe” or downgrade silently). The runtime must reject with `MCC_PASS2_MISSING_OR_FAILED`.

---

## F-05 Test Vectors (Minimum Required)

These are minimum unit-test fixtures for any validator/runtime implementation.

### PASS (6× with B2 buffered + D=2)
- `A / D / B / C / B / D`
- MCC Pass 2: adjacency PASS; density GREEN/YELLOW; node permissions PASS

### FAIL (6× with B→B adjacency)
- `A / D / B / B / C / D`
- Expected: MCC emits `MCC_ADJACENCY_VIOLATION` → reject

### FAIL (6× without required D-minimum)
- `A / B / C / B / C / C`
- Expected: DCC emits `MCC_D_MINIMUM_VIOLATED` → reject

### FAIL (3–5× with B2)
- `A / B / C / B` (4× example)
- Expected: DCC emits `MCC_DAY_B_FREQUENCY_EXCEEDED` → reject

### FAIL (6× with B2 but MCC not run)
- `A / D / B / C / B / D` with no MCC pass invoked
- Expected: reject with `MCC_PASS2_MISSING_OR_FAILED`

---

## F-06 Reason Code Manifest (Registry Sync Requirement)

This document assumes a **global reason-code registry** exists (see `global_reason_codes_v1_0.json`) and that the runtime rejects unregistered codes. Therefore, the following codes **must** be present in the registry with correct namespace and allowed passes.

### DCC Pass 1 (namespace: DCC)
- `MCC_FREQUENCY_NOT_SUPPORTED`
- `MCC_DAY_A_FREQUENCY_EXCEEDED`
- `MCC_DAY_B_FREQUENCY_EXCEEDED`
- `MCC_D_MINIMUM_VIOLATED`
- `MCC_PATTERN_BALANCE_VIOLATED`
- `MCC_DAY_D_INTENT_VIOLATION`
- `MCC_DAY_C_PATTERN_REPETITION`
- `MCC_SESSION_VOLUME_EXCEEDED`
- `MCC_SESSION_DURATION_EXCEEDED`
- `MCC_WORK_BLOCK_INSUFFICIENT`
- `MCC_READINESS_VIOLATION`
- `MCC_READINESS_BAND_MISMATCH`
- `MCC_DAY_A_PATTERN_GUARANTEE_VIOLATED`
- `MCC_MULTI_AXIS_PROGRESSION_VIOLATION`
- `MCC_FAMILY_MULTI_AXIS_VIOLATION`
- `MCC_H4_FREQUENCY_EXCEEDED`
- `MCC_H3_AGGREGATE_EXCEEDED`
- `MCC_BAND_NODE_ILLEGAL_COMBINATION`
- `MCC_BAND3_PATTERN_EXCEEDED`
- `MCC_ECA_COVERAGE_MISSING`
- `MCC_ECA_PATTERN_INCOMPLETE`
- `MCC_VOLUME_CLASS_OVERRIDE_ATTEMPT`
- `PRIMEREPETITIONWARNING`
- `MCC_PRIME_SCOPE_VIOLATION`
- `MCC_COLLAPSE_ESCALATION_TRIGGERED`
- `MCC_CHRONIC_YELLOW_GUARD_TRIGGERED`

### MCC Pass 2 (namespace: MCC)
- `MCC_ADJACENCY_VIOLATION`
- `MCC_CONSECUTIVE_NODE3_EXCEEDED`
- `MCC_DENSITY_LEDGER_EXCEEDED`
- `MCC_NODE_PERMISSION_VIOLATION`
- `MCC_PASS2_MISSING_OR_FAILED` (runtime enforcement code; may be namespaced MCC or RUNTIME)

**Registry Rule:** Any implementation emitting a code not listed here must update the registry first; otherwise the runtime must reject the artifact.

---


# END OF DCC-PHYSIQUE v1.2.1 SPECIFICATION

**Version:** 1.2.1 (Patch F: Frequency Hardening + Enforcement Completion)  
**Last Updated:** 2026-01-26  
**Status:** OPERATIONAL – Fully Enforceable  
**Next Review:** Post-implementation validation with MCC v1.0.1 and first user programs.

---

*DCC-Physique v1.2.1 is the authoritative specification for hypertrophy training under EFL Governance. All implementations must comply with Sections 1–15 and Patches K–P. Questions or implementation issues should be directed to the EFL authority and runtime shell validators.*