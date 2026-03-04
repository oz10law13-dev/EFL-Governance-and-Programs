# EFL Compliance Kernel

Reference implementation of the EFL compliance kernel with frozen JSON specs, a deterministic rule layer, and tests.

## Run tests

```bash
cd efl_kernel
pytest
```

## What is covered

- End-to-end kernel flow tests across step 0-8 guard rails.
- Happy-path KDO validation and decision hash freezing.
- Helper derivations for severity, publish state, lineage keys, canonical hashing, and override caps.
- Registry coverage marker validation.
