# EFL Physique — Program Framework v2.1
## Frequency-Agnostic Generation Envelope for DCC-Physique v1.2 + MCC v1.0

**Status:** PRODUCTION-READY  
**Version:** 2.1.0  
**Date:** 2026-01-25  
**Authority Dependencies:**
- DCC-Physique v1.2 (training law)
- MCC v1.0.0/v1.0.1-PATCHPACK (meso constraint controller)
- ECA v1.2 (exercise catalog)
- Minimal Runtime Shell v1.0 (enforcement infrastructure)

---

## Table of Contents

1. [Core Principle](#1-core-principle)
2. [Frequency Envelope](#2-frequency-envelope)
3. [Day Role Definitions](#3-day-role-definitions)
4. [Frequency Resolution](#4-frequency-resolution)
5. [Schedule Templates](#5-schedule-templates)
6. [Adjacency Constraints](#6-adjacency-constraints)
7. [Magnitude Ceilings](#7-magnitude-ceilings)
8. [Volume Governance](#8-volume-governance)
9. [Progression Governance](#9-progression-governance)
10. [MCC Interaction Layer](#10-mcc-interaction-layer)
11. [Generator Permissions](#11-generator-permissions)
12. [Validation Chain](#12-validation-chain)
13. [Population & Scope](#13-population--scope)
14. [Session Architecture](#14-session-architecture)

---

## 1. Core Principle

**Frequency is a parameter, not a structure.**

Structure is resolved by **day roles**, not by "splits."

- Frequency determines **how many** day roles are instantiated
- Day roles determine **stress magnitude**
- MCC determines **whether the system can tolerate accumulation**

This single principle enables the framework to scale from 2–6+ days per week without breaking DCC legality or MCC accumulation control.

---

## 2. Frequency Envelope

### 2.1 Frequency Classification

```json
{
  "frequency_per_week": {
    "schema_legal": [2, 3, 4, 5, 6, 7, 8],
    "program_supported": [3, 4, 5, 6],
    "runtime_flag_only": [2, 7, 8]
  }
}
```

### 2.2 Classification Definitions

| Frequency | Status | Generator Behavior | Notes |
|-----------|--------|-------------------|-------|
| **2×** | Maintenance-only | No progression, no H3/H4, volume targets at low end | Schema-legal but outside primary program intent |
| **3×** | Supported | Full generation with standard constraints | Minimum recommended for hypertrophy progression |
| **4×** | Supported | Full generation with standard constraints | Classic physique split |
| **5×** | Supported | Full generation with standard constraints | Higher frequency with spacing requirements |
| **6×** | Supported | Full generation with standard constraints | Maximum supported frequency with D-minimum = 2 |
| **7–8×** | Reserved | Runtime-flagged; requires MCC density + adjacency hard checks | Future versions only |

### 2.3 Design Rationale

- **MCC schema** allows `frequency_per_week: 2–8` as schema-legal
- **DCC-Physique v1.2** targets 3–6 as primary intent
- **Framework v2.1** supports 3–6 for full generation; 2× for maintenance; 7–8× reserved

This aligns with MCC's "schema legal vs runtime enforcement" boundary.

---

## 3. Day Role Definitions

Day roles are **semantic contracts** with fixed intent and routing.

```json
{
  "day_role_definitions": {
    "DAY_A": {
      "intent": "Primary mechanical tension",
      "route": "MAX_STRENGTH_EXPRESSION",
      "weekly_max": 1,
      "description": "Heavy compound work; highest load magnitude"
    },
    "DAY_B": {
      "intent": "Hypertrophy volume accumulation",
      "route": "SUBMAX_HYPERTROPHY_VOLUME",
      "weekly_max": 2,
      "description": "Primary hypertrophy driver; permits H3 techniques"
    },
    "DAY_C": {
      "intent": "Capacity and tissue balance",
      "route": "CAPACITY_ACCUMULATION",
      "weekly_max": 1,
      "description": "Corrective, postural, and capacity work"
    },
    "DAY_D": {
      "intent": "Regeneration and low-fatigue stimulus",
      "route": "REGENERATION",
      "weekly_min": 1,
      "description": "Active recovery; movement quality focus"
    }
  }
}
```

### 3.1 Day Role Constraints

- **DAY_A**: At most 1 per week (prevents double heavy days)
- **DAY_B**: At most 2 per week (scales with frequency)
- **DAY_C**: At most 1 per week (tissue balance is additive, not multiplicative)
- **DAY_D**: At least 1 per week (recovery is non-negotiable)

These constraints are **runtime-enforced by MCC** but anticipated by the framework.

---

## 4. Frequency Resolution

### 4.1 Composition Matrix

Frequency determines which day roles appear in the week.

| Frequency | Day Roles Instantiated | Notes |
|-----------|----------------------|-------|
| **2×** | DAY_B, DAY_D | Maintenance-only pattern |
| **3×** | DAY_A, DAY_B, DAY_D | Minimum recommended for progression |
| **4×** | DAY_A, DAY_B, DAY_C, DAY_D | Classic balanced split |
| **5×** | DAY_A, DAY_B, DAY_B, DAY_C, DAY_D | Two hypertrophy days with spacing |
| **6×** | DAY_A, DAY_B, DAY_B, DAY_C, DAY_D, DAY_D | Two hypertrophy + two recovery days |

### 4.2 JSON Encoding

```json
{
  "frequency_resolution_composition": {
    "2": ["DAY_B", "DAY_D"],
    "3": ["DAY_A", "DAY_B", "DAY_D"],
    "4": ["DAY_A", "DAY_B", "DAY_C", "DAY_D"],
    "5": ["DAY_A", "DAY_B", "DAY_B", "DAY_C", "DAY_D"],
    "6": ["DAY_A", "DAY_B", "DAY_B", "DAY_C", "DAY_D", "DAY_D"]
  }
}
```

**Important:** This is composition only, not schedule order. Schedule templates (§5) define legal orderings.

---

## 5. Schedule Templates

### 5.1 Purpose

Prevent adjacency violations **at generation time** by providing default orderings that satisfy spacing constraints.

### 5.2 Template Definitions

```json
{
  "schedule_templates": {
    "2": [
      ["DAY_B", "DAY_D"]
    ],
    "3": [
      ["DAY_A", "DAY_D", "DAY_B"],
      ["DAY_B", "DAY_D", "DAY_A"]
    ],
    "4": [
      ["DAY_A", "DAY_D", "DAY_B", "DAY_C"],
      ["DAY_B", "DAY_D", "DAY_A", "DAY_C"],
      ["DAY_A", "DAY_C", "DAY_D", "DAY_B"]
    ],
    "5": [
      ["DAY_A", "DAY_D", "DAY_B", "DAY_C", "DAY_B"],
      ["DAY_B", "DAY_D", "DAY_A", "DAY_C", "DAY_B"],
      ["DAY_A", "DAY_B", "DAY_D", "DAY_C", "DAY_B"]
    ],
    "6": [
      ["DAY_A", "DAY_D", "DAY_B", "DAY_C", "DAY_B", "DAY_D"],
      ["DAY_B", "DAY_D", "DAY_A", "DAY_C", "DAY_B", "DAY_D"],
      ["DAY_A", "DAY_B", "DAY_D", "DAY_C", "DAY_D", "DAY_B"]
    ]
  }
}
```

### 5.3 Template Selection Rules

1. Generator **must** select one template from the list for the declared frequency
2. Generator **may** rotate templates week-to-week within the same meso
3. Templates guarantee:
   - No DAY_B → DAY_B adjacency
   - At least 1 rest day between high-stress sessions (DAY_A, DAY_B)
   - DAY_D placement optimizes recovery windows

### 5.4 Custom Scheduling

If generator requires custom schedule (e.g., client constraints like "no Monday training"):
- Must validate against adjacency constraints (§6)
- Must pass MCC adjacency validation at commit time

---

## 6. Adjacency Constraints

### 6.1 Forbidden Patterns

These patterns **must not** appear in generated schedules:

```json
{
  "adjacency_constraints": {
    "forbidden_day_role_patterns": [
      "DAY_B → DAY_B"
    ],
    "forbidden_conditional_patterns": [
      "DAY_A(BAND3) → DAY_B",
      "DAY_B → DAY_C(NODE3)"
    ],
    "consecutive_node3_max": 2
  }
}
```

### 6.2 Spacing Requirements

```json
{
  "cooldowns": {
    "DAY_A": {
      "min_days_before_next_high_stress": 1,
      "rationale": "Heavy load requires 48+ hours for CNS/joint recovery"
    },
    "DAY_B": {
      "min_days_before_repeat": 1,
      "rationale": "Hypertrophy volume requires tissue recovery window"
    }
  }
}
```

### 6.3 Authority Boundary

- **Generator**: Should avoid adjacency violations by template selection
- **MCC**: Enforces adjacency at validation time (Pass 2) and restricts or fails as designed
- **DCC**: Does not define adjacency rules (these are MCC-level accumulation controls)

**Correct phrasing:**  
Adjacency constraints are **MCC runtime-enforced** restrictions, not DCC legality rules. The framework anticipates MCC enforcement by providing safe default templates.

---

## 7. Magnitude Ceilings

### 7.1 Day Role Caps

Magnitude ceilings are **frequency-independent** — they depend only on day role.

```json
{
  "day_role_magnitude_caps": {
    "DAY_A": {
      "band_max": 3,
      "node_max": 2,
      "h_nodes_allowed": ["H0", "H1", "H2"],
      "rationale": "MAX_STRENGTH_EXPRESSION permits BAND 3 but restricts density"
    },
    "DAY_B": {
      "band_max": 2,
      "node_max": 2,
      "h_nodes_allowed": ["H0", "H1", "H2", "H3"],
      "rationale": "SUBMAX_HYPERTROPHY_VOLUME permits H3 techniques but caps load"
    },
    "DAY_C": {
      "band_max": 2,
      "node_max": 1,
      "h_nodes_allowed": ["H0", "H1", "H2"],
      "rationale": "CAPACITY_ACCUMULATION emphasizes control over load/density"
    },
    "DAY_D": {
      "band_max": 1,
      "node_max": 1,
      "h_nodes_allowed": ["H0"],
      "rationale": "REGENERATION is truly restorative, not 'sneaky volume'"
    }
  }
}
```

### 7.2 Critical Rules

- **NODE 3 opt-in only**: No day role defaults to NODE 3; requires explicit ECA `node_max = 3` permission
- **H3 aggregate-capped by MCC**: Even though DAY_B allows H3, MCC enforces ≤3 H3 sessions per week
- **Higher frequency ≠ higher intensity**: Magnitude caps do not scale with frequency

---

## 8. Volume Governance

### 8.1 Weekly Targets (Frequency-Independent)

```json
{
  "weekly_volume_targets": {
    "major_muscle_groups": {
      "min_sets": 10,
      "max_sets": 20,
      "definition": "Primary movers: quads, hamstrings, glutes, lats, pecs, delts"
    },
    "minor_muscle_groups": {
      "min_sets": 8,
      "max_sets": 16,
      "definition": "Secondary movers: calves, biceps, triceps, rear delts, traps"
    },
    "postural_stability": {
      "min_sets": 6,
      "max_sets": 12,
      "definition": "Rotator cuff, scapular stabilizers, trunk anti-rotation"
    }
  }
}
```

### 8.2 Distribution Rule

**Volume is distributed across instantiated days — not multiplied by frequency.**

- **3×/week** → higher per-session volume (e.g., 7 sets per major muscle per session)
- **6×/week** → lower per-session volume (e.g., 3 sets per major muscle per session)

Total weekly volume stays within targets regardless of frequency.

### 8.3 Generator Constraint

```json
{
  "volume_distribution_rules": {
    "forbidden": [
      "scale_weekly_totals_with_frequency",
      "add_volume_beyond_targets_to_fill_days"
    ],
    "required": [
      "distribute_targets_evenly_across_instantiated_days",
      "respect_day_role_intent_when_distributing"
    ]
  }
}
```

---

## 9. Progression Governance

### 9.1 Progression Rules (DCC-Aligned)

```json
{
  "progression_rules": {
    "one_axis_per_family_per_week": true,
    "allowed_axes": ["load", "volume", "density", "complexity"],
    "density_progression_restricted_to": ["DAY_B"],
    "complexity_progression_restricted_to": ["DAY_B"],
    "no_progression_on": ["DAY_D"],
    "rationale": "EPA (Exercise Progression Law) v1.0.2 ONE_AXIS enforcement"
  }
}
```

### 9.2 Frequency Does Not Unlock Extra Progression

- **3×/week** and **6×/week** follow the same one-axis-per-family-per-week rule
- Higher frequency enables **better spacing**, not **more axes**

---

## 10. MCC Interaction Layer

### 10.1 MCC Expectations

The framework anticipates MCC's restriction behavior:

```json
{
  "mcc_expectations": {
    "may_downgrade_band": true,
    "may_reduce_node": true,
    "may_reduce_sets": true,
    "may_remove_h3_blocks": true,
    "may_defer_day_role": true,
    "may_rotate_c_day_focus": true,
    "may_suppress_advanced_techniques": true,

    "may_not_add_anything": true,
    "may_not_expand_legality": true
  }
}
```

### 10.2 Generator Implications

Generation must assume:
- Some output will be restricted by MCC based on ledger state
- Proposals should be "MCC-friendly" (conservative magnitude, sensible spacing)
- Over-ambitious proposals will be downgraded or deferred

---

## 11. Generator Permissions

### 11.1 Allowed Actions

```json
{
  "generator_permissions": {
    "may": [
      "select_exercises_from_approved_whitelists",
      "assign_day_roles_from_frequency_resolution",
      "distribute_volume_within_weekly_targets",
      "assign_band_node_within_day_role_caps",
      "rotate_exercises_week_to_week",
      "select_schedule_template_from_frequency_templates"
    ]
  }
}
```

### 11.2 Forbidden Actions

```json
{
  "generator_permissions": {
    "may_not": [
      "invent_day_types",
      "scale_volume_with_frequency",
      "stack_progression_axes",
      "convert_DAY_D_into_work",
      "add_exercises_not_in_whitelist",
      "exceed_magnitude_caps",
      "add_new_day_roles_beyond_frequency_resolution",
      "violate_schedule_template_adjacency_constraints"
    ]
  }
}
```

---

## 12. Validation Chain

### 12.1 Mandatory Validation Sequence

Every generated meso must pass:

```json
{
  "validation_sequence": [
    {
      "step": 1,
      "name": "Pre-Pass Input Validation",
      "checks": ["JSON schema", "ECA resolution", "frequency supported"]
    },
    {
      "step": 2,
      "name": "DCC Session Legality (Pass 1)",
      "checks": ["band/node legality", "session structure", "readiness rules"]
    },
    {
      "step": 3,
      "name": "MCC Exposure Restriction (Pass 2)",
      "checks": ["adjacency", "route saturation", "density ledger", "family-axis locking"]
    },
    {
      "step": 4,
      "name": "Ledger Simulation",
      "checks": ["delta computation", "density projection", "pattern balance"]
    },
    {
      "step": 5,
      "name": "Post-Pass Output Validation",
      "checks": ["output schema", "reason codes", "mode matching"]
    }
  ]
}
```

### 12.2 Failure Behavior

- If any validation step fails → entire generation is invalid
- Generator may not proceed to output without passing all 5 steps

---

## 13. Population & Scope

### 13.1 Target Population

```json
{
  "population_overlay": "adult_physique",
  "training_age_min": "intermediate",
  "age_range": [18, 65],
  "injury_exclusions": [
    "acute_joint_pathology",
    "post_surgical_rehab",
    "chronic_pain_requiring_modification"
  ],
  "readiness_requirements": {
    "GREEN": "normal generation",
    "YELLOW": "MCC downgrade applied",
    "RED": "session deferred or minimal work only"
  }
}
```

### 13.2 Design Intent

- **Hypertrophy-dominant** with recovery protection
- **Intermediate+ training age** (requires structured loading tolerance)
- **Not suitable for**: beginners (need skill acquisition focus) or advanced competitors (need peaking/specialization)

---

## 14. Session Architecture

### 14.1 Session Block Structure (DCC-Locked)

```json
{
  "session_blocks": {
    "PRIME": {
      "target_minutes": [8, 10],
      "intent": "CNS activation, movement prep",
      "exercises": "Activation drills, explosive movements"
    },
    "PREP": {
      "target_minutes": [10, 12],
      "intent": "Joint prep, tissue priming",
      "exercises": "Dynamic stretching, ramping sets"
    },
    "WORK": {
      "target_minutes": [24, 30],
      "minimum_minutes": 24,
      "intent": "Primary training stimulus",
      "exercises": "Compound + assistance lifts"
    },
    "CLEAR": {
      "target_minutes": [5, 8],
      "intent": "Parasympathetic shift, cooldown",
      "exercises": "Static stretching, breathing drills"
    }
  },
  "total_session_minutes": [50, 60]
}
```

### 14.2 Hard Rules

- **WORK block minimum is non-negotiable**: ≥24 minutes
- **CLEAR cannot be skipped or absorbed**: Must exist as distinct block
- **Total session must stay within 50–60 minutes**: Prevents session creep

---

## Appendix A: Example Weekly Schedules

### 3×/week Example
```
Mon: DAY_A (MAX_STRENGTH_EXPRESSION)
Wed: DAY_D (REGENERATION)
Fri: DAY_B (SUBMAX_HYPERTROPHY_VOLUME)
```

### 4×/week Example
```
Mon: DAY_A (MAX_STRENGTH_EXPRESSION)
Tue: DAY_D (REGENERATION)
Thu: DAY_B (SUBMAX_HYPERTROPHY_VOLUME)
Sat: DAY_C (CAPACITY_ACCUMULATION)
```

### 5×/week Example
```
Mon: DAY_A (MAX_STRENGTH_EXPRESSION)
Tue: DAY_D (REGENERATION)
Wed: DAY_B (SUBMAX_HYPERTROPHY_VOLUME)
Fri: DAY_C (CAPACITY_ACCUMULATION)
Sat: DAY_B (SUBMAX_HYPERTROPHY_VOLUME)
```

### 6×/week Example
```
Mon: DAY_A (MAX_STRENGTH_EXPRESSION)
Tue: DAY_D (REGENERATION)
Wed: DAY_B (SUBMAX_HYPERTROPHY_VOLUME)
Thu: DAY_C (CAPACITY_ACCUMULATION)
Fri: DAY_B (SUBMAX_HYPERTROPHY_VOLUME)
Sat: DAY_D (REGENERATION)
```

---

## Appendix B: Authority Hierarchy Summary

| Layer | Role | Mutable | Enforcement |
|-------|------|---------|-------------|
| **DCC-Physique v1.2** | Training law | ❌ | Pass 1 (LAW mode) |
| **ECA v1.2** | Exercise definitions | ❌ | Pre-pass validator |
| **MCC v1.0** | Accumulation restriction | ❌ | Pass 2 (CONTROL mode) |
| **Program Framework v2.1** | Generation envelope | ✅ | Pre-generation constraints |
| **Generator (ChatGPT)** | Instance creator | ✅ | Bounded by framework |

---

**END OF SPECIFICATION**

Document Version: 2.1.0  
Last Updated: 2026-01-25  
Status: PRODUCTION-READY

**Changes from v2.0:**
- Added frequency classification (schema-legal vs program-supported)
- Added schedule templates for 3–6× frequencies
- Added explicit adjacency constraints
- Clarified authority boundary (DCC vs MCC vs Framework)
- Added validation chain with 5-step sequence
- Added appendices with example schedules and authority hierarchy
