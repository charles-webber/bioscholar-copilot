import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_TRACE_FILE = (
    Path(__file__).resolve().parent
    / "outputs"
    / "trace.jsonl"
)


def as_int(value: Any) -> int:
    """把可能缺失的 token 字段安全转换成整数。"""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def collect_usage(
    trace_file: Path,
) -> dict[str, int | float]:
    """汇总 trace 中的模型调用次数和 token 用量。"""
    totals: dict[str, int | float] = {
        "calls": 0,
        "successful_calls": 0,
        "failed_calls": 0,
        "unreadable_calls": 0,
        "calls_with_usage": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "cached_prompt_tokens": 0,
        "total_tokens": 0,
        "average_total_tokens": 0.0,
    }

    if not trace_file.exists():
        return totals

    for line in trace_file.read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        if record.get("tools") != "generate_text":
            continue

        totals["calls"] += 1
        observation = record.get("observation")

        if not isinstance(observation, dict):
            totals["unreadable_calls"] += 1
            continue

        if not observation.get("ok"):
            totals["failed_calls"] += 1
            continue

        totals["successful_calls"] += 1
        usage = observation.get("usage")

        if not isinstance(usage, dict):
            continue

        totals["calls_with_usage"] += 1
        totals["prompt_tokens"] += as_int(
            usage.get("prompt_tokens")
        )
        totals["completion_tokens"] += as_int(
            usage.get("completion_tokens")
        )
        totals["total_tokens"] += as_int(
            usage.get("total_tokens")
        )

        completion_details = (
            usage.get("completion_tokens_details") or {}
        )
        prompt_details = (
            usage.get("prompt_tokens_details") or {}
        )

        if isinstance(completion_details, dict):
            totals["reasoning_tokens"] += as_int(
                completion_details.get("reasoning_tokens")
            )

        if isinstance(prompt_details, dict):
            totals["cached_prompt_tokens"] += as_int(
                prompt_details.get("cached_tokens")
            )

    calls_with_usage = int(totals["calls_with_usage"])

    if calls_with_usage:
        totals["average_total_tokens"] = round(
            int(totals["total_tokens"]) / calls_with_usage,
            2,
        )

    return totals


def main() -> None:
    parser = argparse.ArgumentParser(
        description="汇总生物医学 Agent 的模型 token 用量。"
    )
    parser.add_argument(
        "--trace-file",
        type=Path,
        default=DEFAULT_TRACE_FILE,
        help="trace.jsonl 的路径。",
    )
    args = parser.parse_args()

    report = collect_usage(args.trace_file)
    output = {
        "trace_file": str(args.trace_file.resolve()),
        **report,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
