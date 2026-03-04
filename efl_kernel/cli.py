from __future__ import annotations

import argparse
import json
import sys

from efl_kernel.kernel.audit_store import AuditStore
from efl_kernel.kernel.kernel import KernelRunner
from efl_kernel.kernel.ral import RAL_SPEC
from efl_kernel.kernel.sqlite_dependency_provider import SqliteDependencyProvider

_KNOWN_MODULES = set(RAL_SPEC["moduleRegistration"].keys())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="EFL Kernel evaluation CLI")
    parser.add_argument("--module", required=True, help="Module ID (SESSION, MESO, MACRO, GOVERNANCE)")
    parser.add_argument("--input", required=True, dest="input_path", help="Path to JSON payload file")
    parser.add_argument("--db", default="efl_audit.db", dest="db_path", help="Path to SQLite audit database")
    args = parser.parse_args(argv)

    if args.module not in _KNOWN_MODULES:
        print(
            f"Error: unknown module {args.module!r}. Valid modules: {sorted(_KNOWN_MODULES)}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with open(args.input_path, encoding="utf-8") as f:
            payload = json.load(f)
    except FileNotFoundError:
        print(f"Error: input file not found: {args.input_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {args.input_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        audit_store = AuditStore(args.db_path)
        dep = SqliteDependencyProvider(audit_store)
        kdo = KernelRunner(dep).evaluate(payload, args.module)
        audit_store.commit_kdo(kdo)
        print(json.dumps(kdo.__dict__, sort_keys=True, indent=2))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
