"""Read-only Hokea check; no Docker/Kubernetes/account action.

Fails if the installed Hokea lacks a class, method or constructor option the adapter uses.
Reports, without failing, whether its files differ from the reference revision.
"""
import argparse
import importlib
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.harness.hokea_adapter import REQUIRED_API, describe_package, verify_api


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, help="hokea package directory to describe; default: installed package")
    args = parser.parse_args()
    spec = importlib.util.find_spec("hokea")
    if spec is None or spec.origin is None:
        parser.error("Hokea is not installed; install the course Hokea package in your local environment")
    package = args.package or Path(spec.origin).parent
    print(json.dumps(describe_package(package), indent=2))
    for mode in REQUIRED_API:
        print(f"{mode}: {verify_api(mode, importlib.import_module).__name__} provides the adapter API")


if __name__ == "__main__":
    main()
