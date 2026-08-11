"""Generate local, synthetic files used by the browser upload test.

The files are written below ``artifacts/`` by default and are intentionally
not tracked.  Their content is produced by the same material factory as the
controlled Demo API, so the manual-upload path exercises the real parsers.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.demo import scenario_materials  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/e2e-materials"),
        help="Directory receiving the synthetic upload files.",
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    for _, filename, _, content in scenario_materials("DEMO-NORMAL-001"):
        (args.output / filename).write_bytes(content)

    print(f"generated_materials={len(list(args.output.iterdir()))}")


if __name__ == "__main__":
    main()
