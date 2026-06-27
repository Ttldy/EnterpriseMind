from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.evaluation.benchmark_compare import compare_reports


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare EnterpriseMind benchmark reports."
    )
    parser.add_argument("baseline")
    parser.add_argument("enhanced")
    parser.add_argument(
        "--output",
        required=True,
        help="UTF-8 JSON output path.",
    )
    return parser.parse_args()


def read_json(
    path: str,
) -> dict[str, object]:
    return json.loads(
        Path(path).read_text(encoding="utf-8")
    )


def main() -> None:
    args = parse_args()
    result = compare_reports(
        baseline=read_json(args.baseline),
        enhanced=read_json(args.enhanced),
    )
    output = Path(args.output)
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "case_count": result["case_count"],
                "interview_summary": result[
                    "interview_summary"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
