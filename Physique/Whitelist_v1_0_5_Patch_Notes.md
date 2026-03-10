# Whitelist v1.0.5 Patch Notes

## 1. Overview

Expands the exercise whitelist from 30 to 200 exercises across 19 family-block
categories. Introduces family-block ID renumbering for organizational clarity.

## 2. ID Renumbering

All 30 original exercises are preserved but renumbered into family-block ranges:

| Old ID | Exercise | New ID | Block |
|--------|----------|--------|-------|
| 0001 | Back Squat | 0001 | Squat |
| 0002 | Front Squat | 0002 | Squat |
| 0030 | Tempo Squat (5s ecc) | 0003 | Squat |
| 0003 | Romanian Deadlift | 0013 | Hinge |
| 0004 | Conventional Deadlift | 0014 | Hinge |
| 0020 | Hip Thrust | 0016 | Hinge |
| 0005 | Leg Press | 0015 | Hinge |
| 0006 | Bulgarian Split Squat | 0025 | Lunge/Split |
| 0007 | Walking Lunge | 0026 | Lunge/Split |
| 0008 | Barbell Bench Press | 0035 | Horizontal Press |
| 0009 | Incline DB Press | 0036 | Horizontal Press |
| 0010 | Barbell Overhead Press | 0047 | Vertical Press |
| 0011 | Pull-Up | 0055 | Horizontal Pull |
| 0013 | Seated Cable Row | 0056 | Horizontal Pull |
| 0012 | Barbell Bent-Over Row | 0067 | Vertical Pull |
| 0014 | Lat Pulldown | 0068 | Vertical Pull |
| 0017 | DB Biceps Curl | 0077 | Biceps |
| 0016 | Cable Triceps Pushdown | 0085 | Triceps |
| 0015 | DB Lateral Raise | 0093 | Shoulder Isolation |
| 0018 | Leg Extension | 0101 | Knee Ext/Flex |
| 0019 | Lying Leg Curl | 0106 | Knee Ext/Flex |
| 0023 | Plank | 0114 | Core |
| 0026 | Cable Woodchop | 0116 | Core |
| 0025 | Farmer Carry | 0124 | Carry/Locomotion |
| 0024 | Sled Drag (Light) | 0127 | Corrective/Prehab |
| 0022 | Band External Rotation | 0129 | Corrective/Prehab |
| 0021 | Face Pull | 0130 | Corrective/Prehab |
| 0027 | Rest-Pause Set | 0135 | Technique Modifiers |
| 0028 | Myo-Reps | 0136 | Technique Modifiers |
| 0029 | Drop Set | 0137 | Technique Modifiers |

## 3. Property Changes

| Exercise | Property | Old Value | New Value | Rationale |
|----------|----------|-----------|-----------|-----------|
| Hip Thrust | volume_class | ASSISTANCE | PRIMARY | Upgraded to primary hinge |
| Walking Lunge | node_max | 3 | 2 | Tightened for safety |
| Plank | day_role_allowed | D,CLEAR | B,C,D | CLEAR removed, B,C added |

## 4. Family-Block ID Ranges

| Block | Range | Family |
|-------|-------|--------|
| 1 | 0001-0012 | Squat |
| 2 | 0013-0024 | Hinge |
| 3 | 0025-0034 | Lunge/Split |
| 4 | 0035-0046 | Horizontal Press |
| 5 | 0047-0054 | Vertical Press |
| 6 | 0055-0066 | Horizontal Pull (Rows) |
| 7 | 0067-0076 | Vertical Pull |
| 8 | 0077-0084 | Biceps/Elbow Flexion |
| 9 | 0085-0092 | Triceps/Elbow Extension |
| 10 | 0093-0100 | Shoulder Isolation |
| 11 | 0101-0110 | Knee Extension/Flexion |
| 12 | 0111-0118 | Core |
| 13 | 0119-0126 | Carry/Locomotion |
| 14 | 0127-0134 | Corrective/Prehab |
| 15 | 0135-0140 | Technique Modifiers |
| 16 | 0141-0150 | Hip/Glute Isolation |
| 17 | 0151-0170 | Machine Compound |
| 18 | 0171-0190 | Cable/Band Accessories |
| 19 | 0191-0200 | Specialty/Sport |

## 5. Alias Table Updates

- 12 existing ECA-FAMILY aliases updated to point to new canonical IDs
- 28 backward-compat aliases added (ECA-PHY-v104-NNNN format)
- documentHash recomputed

## 6. Tempo Governance Update

Added `ACCESSORY_COMPOUND: 2` to `eccentric_minimum_rules.class_based_minimums`.

## 7. Test Impact

- All test files with old IDs mechanically remapped
- Count assertions updated: 30 -> 200
- SFI test adjusted for Walking Lunge node_max change (uses Bulgarian Split Squat instead)
- 10 new whitelist validation tests in `test_whitelist_v105.py`
- Suite: 566 passed, 25 skipped (pre-existing skip/fail unchanged)
