from __future__ import annotations

import argparse
import json
from pathlib import Path


def discover_test_files(tests_root: Path) -> list[str]:
    return sorted(
        str(path.as_posix())
        for path in tests_root.rglob("test_*.py")
        if "__pycache__" not in path.parts
    )


def split_baseline(test_files: list[str], shard_count: int) -> list[list[str]]:
    shards: list[list[str]] = [[] for _ in range(shard_count)]

    for index, test_file in enumerate(test_files):
        shard_index = index % shard_count
        shards[shard_index].append(test_file)

    return shards


def load_timings(timings_file: Path) -> dict[str, float]:
    raw = json.loads(timings_file.read_text(encoding="utf-8"))

    timings: dict[str, float] = {}

    if isinstance(raw, list):
        for item in raw:
            test_file = item.get("test_file")
            duration = item.get("duration_seconds")
            if test_file is not None and duration is not None:
                timings[str(test_file)] = float(duration)

    elif isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(value, dict):
                duration = value.get("duration_seconds") or value.get("duration")
            else:
                duration = value

            if duration is not None:
                timings[str(key)] = float(duration)

    return timings


def split_by_timing(
    test_files: list[str],
    timings: dict[str, float],
    shard_count: int,
) -> list[list[str]]:
    shards: list[list[str]] = [[] for _ in range(shard_count)]
    shard_durations = [0.0 for _ in range(shard_count)]

    sorted_tests = sorted(
        test_files,
        key=lambda test_file: timings.get(test_file, 0.0),
        reverse=True,
    )

    for test_file in sorted_tests:
        target_index = min(range(shard_count), key=lambda index: shard_durations[index])
        shards[target_index].append(test_file)
        shard_durations[target_index] += timings.get(test_file, 0.0)

    return shards


def build_plan(
    shards: list[list[str]],
    timings: dict[str, float] | None,
) -> dict:
    shard_plans = []

    for index, shard in enumerate(shards, start=1):
        estimated_duration = 0.0
        if timings is not None:
            estimated_duration = sum(timings.get(test_file, 0.0) for test_file in shard)

        shard_plans.append(
            {
                "shard_id": index,
                "test_count": len(shard),
                "estimated_duration_seconds": round(estimated_duration, 4),
                "tests": shard,
            }
        )

    estimated_durations = [
        shard_plan["estimated_duration_seconds"] for shard_plan in shard_plans
    ]

    avg_duration = (
        sum(estimated_durations) / len(estimated_durations)
        if estimated_durations
        else 0.0
    )

    max_duration = max(estimated_durations) if estimated_durations else 0.0

    imbalance_ratio = (
        max_duration / avg_duration
        if avg_duration > 0
        else None
    )

    return {
        "shard_count": len(shards),
        "total_test_files": sum(len(shard) for shard in shards),
        "estimated_durations_seconds": estimated_durations,
        "estimated_max_duration_seconds": round(max_duration, 4),
        "estimated_avg_duration_seconds": round(avg_duration, 4),
        "estimated_imbalance_ratio": (
            round(imbalance_ratio, 4)
            if imbalance_ratio is not None
            else None
        ),
        "shards": shard_plans,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Select pytest files for CI sharding."
    )
    parser.add_argument(
        "--mode",
        choices=["baseline", "timing"],
        required=True,
    )
    parser.add_argument(
        "--tests-root",
        default="tests",
    )
    parser.add_argument(
        "--timings-file",
        default=None,
    )
    parser.add_argument(
        "--shard-id",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--shard-count",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--output",
        default="shard_tests.txt",
    )
    parser.add_argument(
        "--plan-output",
        default="shard_plan.json",
    )

    args = parser.parse_args()

    tests_root = Path(args.tests_root)
    test_files = discover_test_files(tests_root)

    if not test_files:
        raise SystemExit(f"No test files found under {tests_root}")

    if args.shard_id < 1 or args.shard_id > args.shard_count:
        raise SystemExit(
            f"shard-id must be between 1 and shard-count "
            f"({args.shard_id} > {args.shard_count})"
        )

    timings: dict[str, float] | None = None

    if args.mode == "baseline":
        shards = split_baseline(test_files, args.shard_count)
    else:
        if not args.timings_file:
            raise SystemExit("--timings-file is required in timing mode")

        timings_file = Path(args.timings_file)
        if not timings_file.exists():
            raise SystemExit(f"Timings file not found: {timings_file}")

        timings = load_timings(timings_file)
        shards = split_by_timing(test_files, timings, args.shard_count)

    selected_tests = shards[args.shard_id - 1]

    Path(args.output).write_text(
        "\n".join(selected_tests) + "\n",
        encoding="utf-8",
    )

    plan = build_plan(shards, timings)

    Path(args.plan_output).write_text(
        json.dumps(plan, indent=2),
        encoding="utf-8",
    )

    print(
        f"Selected {len(selected_tests)} test files "
        f"for shard {args.shard_id}/{args.shard_count}"
    )


if __name__ == "__main__":
    main()