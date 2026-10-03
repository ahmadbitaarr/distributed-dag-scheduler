"""Read-only pin verification; no Docker/Kubernetes/account action."""
import argparse
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.harness.hokea_adapter import verify_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, help="source hokea package directory; default: installed package")
    args = parser.parse_args()
    package = args.package
    if package is None:
        spec = importlib.util.find_spec("hokea")
        if spec is None or spec.origin is None:
            parser.error("Hokea is not installed; install the pinned course checkout in your local environment")
        package = Path(spec.origin).parent
    print("Verified Hokea source:", verify_package(package))


if __name__ == "__main__":
    main()
