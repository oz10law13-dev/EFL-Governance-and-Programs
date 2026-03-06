# EFL Physique — Exercise Whitelist Schema v1.0
## Safe Exercise Selection for Program Framework v2.1

**Status:** PRODUCTION-READY  
**Version:** 1.0.0  
**Date:** 2026-01-25  
**Parent Documents:**
- EFL Physique Program Framework v2.1
- ECA v1.2 (Exercise Catalog Authority)
- DCC-Physique v1.2

---

## Purpose

This schema defines how exercises are organized, filtered, and selected during generation to ensure:

1. Only pre-approved exercises are used
2. Exercises match day role magnitude caps
3. Movement family balance is maintainable
4. Generator cannot invent or drift from catalog

---

## 1. Whitelist Structure

### 1.1 Top-Level Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EFL Physique Exercise Whitelist v1.0",
  "type": "object",
  "required": ["whitelist_version", "eca_version", "population", "movement_families"],
  "properties": {
    "whitelist_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Semantic version of this whitelist"
    },
    "eca_version": {
      "type": "string",
      "pattern": "^ECA-v\\d+\\.\\d+$",
      "description": "ECA catalog version this whitelist references"
    },
    "population": {
      "type": "string",
      "enum": ["adult_physique", "adult_physique_40plus"],
      "description": "Target population for this whitelist"
    },
    "movement_families": {
      "type": "object",
      "description": "Exercises organized by movement family"
    }
  }
}
```

---

## 2. Movement Family Organization

### 2.1 Movement Family Structure

Each movement family contains exercises grouped by role permissions.

```json
{
  "movement_families": {
    "squat": {
      "family_description": "Knee-dominant lower body movements",
      "exercises": [
        {
          "eca_id": "ECA-SQUAT-001",
          "name": "Back Squat (High Bar)",
          "movement_family": "squat",
          "band_range": [2, 3],
          "node_max": 2,
          "h_node": "H1",
          "volume_class": "PRIMARY",
          "push_pull": "none",
          "horiz_vert": "sagittal",
          "day_roles_allowed": ["DAY_A", "DAY_B"],
          "contraindications": [],
          "equipment": ["barbell", "rack"],
          "notes": "Primary compound; suitable for MAX_STRENGTH_EXPRESSION"
        }
      ]
    }
  }
}
```

### 2.2 Required Movement Families

Every whitelist must include:

- `squat` (knee-dominant lower)
- `hinge` (hip-dominant lower)
- `press` (horizontal + vertical push)
- `pull` (horizontal + vertical pull)
- `carry` (loaded carries, farmer walks)
- `isolate` (single-joint accessory)
- `trunk` (anti-rotation, anti-extension, anti-flexion)

---

## 3. Exercise Entry Schema

### 3.1 Required Fields

```json
{
  "exercise_entry": {
    "type": "object",
    "required": [
      "eca_id",
      "name",
      "movement_family",
      "band_range",
      "node_max",
      "h_node",
      "volume_class",
      "day_roles_allowed"
    ],
    "properties": {
      "eca_id": {
        "type": "string",
        "pattern": "^ECA-[A-Z0-9_-]+$",
        "description": "Canonical ECA identifier"
      },
      "name": {
        "type": "string",
        "description": "Human-readable exercise name"
      },
      "movement_family": {
        "type": "string",
        "enum": ["squat", "hinge", "press", "pull", "carry", "isolate", "trunk"]
      },
      "band_range": {
        "type": "array",
        "items": {"type": "integer", "minimum": 0, "maximum": 3},
        "minItems": 2,
        "maxItems": 2,
        "description": "[min_band, max_band] this exercise supports"
      },
      "node_max": {
        "type": "integer",
        "minimum": 1,
        "maximum": 3,
        "description": "Maximum NODE permitted (NODE 3 opt-in)"
      },
      "h_node": {
        "type": "string",
        "enum": ["H0", "H1", "H2", "H3", "H4"],
        "description": "Hypertrophy complexity classification"
      },
      "volume_class": {
        "type": "string",
        "enum": ["PRIMARY", "ASSISTANCE", "ACCESSORY"],
        "description": "Immutable ECA volume weighting"
      },
      "day_roles_allowed": {
        "type": "array",
        "items": {"type": "string", "enum": ["DAY_A", "DAY_B", "DAY_C", "DAY_D"]},
        "minItems": 1,
        "description": "Which day roles may use this exercise"
      }
    }
  }
}
```

### 3.2 Optional Fields

```json
{
  "optional_fields": {
    "push_pull": {
      "type": "string",
      "enum": ["push", "pull", "mixed", "none"],
      "description": "Force direction for pattern balance"
    },
    "horiz_vert": {
      "type": "string",
      "enum": ["horizontal", "vertical", "sagittal", "frontal"],
      "description": "Primary plane of motion"
    },
    "contraindications": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Conditions that prohibit this exercise"
    },
    "equipment": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Required equipment"
    },
    "notes": {
      "type": "string",
      "description": "Programming notes or coaching cues"
    },
    "progression_axis": {
      "type": "string",
      "enum": ["load", "volume", "density", "complexity", "none"],
      "description": "Default progression axis for this exercise"
    }
  }
}
```

---

## 4. Day Role Filtering Rules

### 4.1 Filter Logic

When selecting exercises for a day role, apply filters in sequence:

1. **Movement family match** — exercise.movement_family must match desired family
2. **Day role permission** — day_role must be in exercise.day_roles_allowed
3. **Band compatibility** — proposed band must be within exercise.band_range
4. **Node permission** — proposed node must be ≤ exercise.node_max
5. **H-node compatibility** — exercise.h_node must be allowed by day role caps

### 4.2 Filter Examples

#### Example 1: DAY_A (MAX_STRENGTH_EXPRESSION)

```
Day role caps:
  band_max = 3
  node_max = 2
  h_nodes_allowed = [H0, H1, H2]

Filter:
  exercise.day_roles_allowed contains "DAY_A"
  AND exercise.band_range[1] >= 3
  AND exercise.node_max >= 2
  AND exercise.h_node in [H0, H1, H2]
```

#### Example 2: DAY_D (REGENERATION)

```
Day role caps:
  band_max = 1
  node_max = 1
  h_nodes_allowed = [H0]

Filter:
  exercise.day_roles_allowed contains "DAY_D"
  AND exercise.band_range[0] <= 1
  AND exercise.node_max >= 1
  AND exercise.h_node == H0
```

---

## 5. Whitelist Validation Rules

### 5.1 Coverage Requirements

Every whitelist must provide:

- **Minimum 3 exercises per movement family** for each day role
- **At least 1 PRIMARY exercise per major movement family** (squat, hinge, press, pull)
- **Balance across push/pull** (≥40% each in available exercises)
- **Balance across horizontal/vertical** (≥35% each)

### 5.2 Validation Schema

```json
{
  "whitelist_validation": {
    "min_exercises_per_family_per_role": 3,
    "required_primary_families": ["squat", "hinge", "press", "pull"],
    "min_primary_exercises_per_major_family": 1,
    "pattern_balance_minimums": {
      "push_percent": 40,
      "pull_percent": 40,
      "horizontal_percent": 35,
      "vertical_percent": 35
    }
  }
}
```

---

## 6. Example Whitelist Entries

### 6.1 Squat Family Example

```json
{
  "squat": {
    "family_description": "Knee-dominant lower body movements",
    "exercises": [
      {
        "eca_id": "ECA-SQUAT-001",
        "name": "Back Squat (High Bar)",
        "movement_family": "squat",
        "band_range": [2, 3],
        "node_max": 2,
        "h_node": "H1",
        "volume_class": "PRIMARY",
        "day_roles_allowed": ["DAY_A", "DAY_B"],
        "push_pull": "none",
        "horiz_vert": "sagittal",
        "equipment": ["barbell", "rack"],
        "progression_axis": "load"
      },
      {
        "eca_id": "ECA-SQUAT-002",
        "name": "Front Squat",
        "movement_family": "squat",
        "band_range": [2, 3],
        "node_max": 2,
        "h_node": "H1",
        "volume_class": "PRIMARY",
        "day_roles_allowed": ["DAY_A", "DAY_B"],
        "push_pull": "none",
        "horiz_vert": "sagittal",
        "equipment": ["barbell", "rack"],
        "progression_axis": "load"
      },
      {
        "eca_id": "ECA-SQUAT-010",
        "name": "Goblet Squat",
        "movement_family": "squat",
        "band_range": [1, 2],
        "node_max": 2,
        "h_node": "H1",
        "volume_class": "ASSISTANCE",
        "day_roles_allowed": ["DAY_B", "DAY_C", "DAY_D"],
        "push_pull": "none",
        "horiz_vert": "sagittal",
        "equipment": ["dumbbell", "kettlebell"],
        "progression_axis": "volume"
      }
    ]
  }
}
```

### 6.2 Pull Family Example

```json
{
  "pull": {
    "family_description": "Pulling movements (horizontal + vertical)",
    "exercises": [
      {
        "eca_id": "ECA-PULL-001",
        "name": "Barbell Row (Bent)",
        "movement_family": "pull",
        "band_range": [2, 3],
        "node_max": 2,
        "h_node": "H1",
        "volume_class": "PRIMARY",
        "day_roles_allowed": ["DAY_A", "DAY_B"],
        "push_pull": "pull",
        "horiz_vert": "horizontal",
        "equipment": ["barbell"],
        "progression_axis": "load"
      },
      {
        "eca_id": "ECA-PULL-005",
        "name": "Pull-Up (Pronated Grip)",
        "movement_family": "pull",
        "band_range": [0, 2],
        "node_max": 2,
        "h_node": "H1",
        "volume_class": "PRIMARY",
        "day_roles_allowed": ["DAY_A", "DAY_B", "DAY_C"],
        "push_pull": "pull",
        "horiz_vert": "vertical",
        "equipment": ["pull-up bar"],
        "progression_axis": "load"
      },
      {
        "eca_id": "ECA-PULL-020",
        "name": "Face Pull (Cable)",
        "movement_family": "pull",
        "band_range": [1, 2],
        "node_max": 2,
        "h_node": "H2",
        "volume_class": "ACCESSORY",
        "day_roles_allowed": ["DAY_B", "DAY_C", "DAY_D"],
        "push_pull": "pull",
        "horiz_vert": "horizontal",
        "equipment": ["cable"],
        "progression_axis": "volume"
      }
    ]
  }
}
```

### 6.3 Trunk Family Example

```json
{
  "trunk": {
    "family_description": "Anti-rotation, anti-extension, anti-flexion",
    "exercises": [
      {
        "eca_id": "ECA-TRUNK-001",
        "name": "Pallof Press (Cable)",
        "movement_family": "trunk",
        "band_range": [1, 2],
        "node_max": 2,
        "h_node": "H0",
        "volume_class": "ACCESSORY",
        "day_roles_allowed": ["DAY_C", "DAY_D"],
        "push_pull": "none",
        "horiz_vert": "frontal",
        "equipment": ["cable"],
        "progression_axis": "volume"
      },
      {
        "eca_id": "ECA-TRUNK-010",
        "name": "Dead Bug",
        "movement_family": "trunk",
        "band_range": [0, 1],
        "node_max": 1,
        "h_node": "H0",
        "volume_class": "ACCESSORY",
        "day_roles_allowed": ["DAY_C", "DAY_D"],
        "push_pull": "none",
        "horiz_vert": "sagittal",
        "equipment": ["bodyweight"],
        "progression_axis": "complexity"
      }
    ]
  }
}
```

---

## 7. Generator Selection Algorithm

### 7.1 Selection Process

```python
def select_exercises(day_role, movement_family, proposed_band, proposed_node):
    # Step 1: Load whitelist for population
    whitelist = load_whitelist("adult_physique")

    # Step 2: Get movement family exercises
    family_exercises = whitelist["movement_families"][movement_family]["exercises"]

    # Step 3: Apply filters
    filtered = []
    for exercise in family_exercises:
        if (day_role in exercise["day_roles_allowed"] and
            exercise["band_range"][0] <= proposed_band <= exercise["band_range"][1] and
            exercise["node_max"] >= proposed_node and
            exercise["h_node"] in get_allowed_h_nodes(day_role)):
            filtered.append(exercise)

    # Step 4: Return eligible exercises
    return filtered
```

### 7.2 Selection Constraints

- **PRIMARY exercises prioritized** for main compound movements
- **ASSISTANCE/ACCESSORY** fill remaining volume targets
- **No duplication** within same session (unless explicitly permitted)
- **Rotation encouraged** week-to-week for variety

---

## 8. Whitelist Versioning

### 8.1 Version Format

`<major>.<minor>.<patch>`

- **Major**: Breaking changes (remove exercises, change structure)
- **Minor**: Add exercises, add optional fields
- **Patch**: Correct errors, update notes

### 8.2 Version Compatibility

- Whitelist version must be compatible with ECA version declared
- Generator must validate whitelist version before selection
- Mismatch → fail-closed with `WHITELIST_VERSION_MISMATCH`

---

## 9. Implementation Checklist

For each whitelist:

- [ ] Declare `whitelist_version`, `eca_version`, `population`
- [ ] Include all 7 required movement families
- [ ] Minimum 3 exercises per family per day role
- [ ] At least 1 PRIMARY per major family (squat, hinge, press, pull)
- [ ] Validate pattern balance (push/pull, horiz/vert)
- [ ] All exercises have required fields
- [ ] All `eca_id` values exist in ECA catalog
- [ ] Day role filtering rules tested
- [ ] JSON schema validation passes

---

## 10. Usage in Generation

### 10.1 Generator Workflow

1. Load whitelist for declared population
2. For each session slot:
   - Determine day role
   - Determine required movement families (based on weekly balance)
   - Filter whitelist by day role + magnitude
   - Select exercises maintaining pattern balance
3. Validate selection:
   - All ECA IDs valid
   - Volume targets met
   - Pattern balance maintained
   - No prohibited combinations

### 10.2 Validation Example

```json
{
  "session": {
    "day_role": "DAY_A",
    "exercises": [
      {"eca_id": "ECA-SQUAT-001", "band": 3, "node": 2},
      {"eca_id": "ECA-PULL-001", "band": 2, "node": 2},
      {"eca_id": "ECA-HINGE-002", "band": 2, "node": 2}
    ]
  },
  "validation": {
    "all_eca_ids_in_whitelist": true,
    "all_day_role_permissions_valid": true,
    "magnitude_caps_respected": true,
    "pattern_balance_on_track": true,
    "status": "VALID"
  }
}
```

---

**END OF SCHEMA**

Document Version: 1.0.0  
Last Updated: 2026-01-25  
Status: PRODUCTION-READY

**Next Steps:**
1. Create first concrete whitelist (adult_physique v1.0.0)
2. Test filtering logic with all day roles
3. Generate sample 4-week meso using whitelist
