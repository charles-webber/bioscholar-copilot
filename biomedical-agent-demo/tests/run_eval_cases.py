import json
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch


PROJECT_DIR = Path(__file__).resolve().parents[1]

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import agent_fourday
import biomedical_agent


CASES_FILE = PROJECT_DIR / "biomedical_eval_cases.json"


def fake_generate_text(
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int,
) -> dict[str, Any]:
    """返回安全的假回答，确保评测不访问中转站。"""
    return {
        "ok": True,
        "text": (
            "这是离线评测回答。\n\n"
            "证据来源：\n"
            "[来源: notes_long.txt | ref: offline-eval]"
        ),
        "model": "fake-model",
        "api_style": "chat_completions",
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


def evaluate_case(
    case: dict[str, Any],
    result: dict[str, Any],
) -> list[str]:
    """返回当前用例不符合预期的原因。"""
    reasons: list[str] = []
    expected_ok = case["expected_ok"]
    actual_ok = result.get("ok")

    if actual_ok != expected_ok:
        reasons.append(
            f"ok 预期 {expected_ok}，实际 {actual_ok}"
        )

    expected_topic = case.get("expected_topic")
    actual_topic = str(result.get("resolved_topic", ""))

    if (
        expected_topic
        and expected_topic.lower() not in actual_topic.lower()
    ):
        reasons.append(
            f"主题预期包含 {expected_topic}，实际 {actual_topic}"
        )

    expected_code = case.get("expected_error_code")
    actual_code = (result.get("error") or {}).get("code")

    if expected_code and actual_code != expected_code:
        reasons.append(
            f"错误码预期 {expected_code}，实际 {actual_code}"
        )

    if actual_ok and result.get("user_task") != case["task"]:
        reasons.append("成功结果没有完整保留 user_task")

    return reasons


def display_actual(result: dict[str, Any]) -> str:
    """生成便于阅读的实际结果摘要。"""
    if result.get("ok"):
        return str(result.get("resolved_topic", "ok=true"))

    return str(
        (result.get("error") or {}).get("code", "未知错误")
    )


def main() -> None:
    cases = json.loads(
        CASES_FILE.read_text(encoding="utf-8")
    )
    rows: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory() as temp_folder:
        output_dir = Path(temp_folder)
        trace_file = output_dir / "trace.jsonl"

        with (
            patch.object(
                biomedical_agent,
                "BIO_OUTPUT_DIR",
                output_dir,
            ),
            patch.object(
                biomedical_agent,
                "BIO_TRACE_FILE",
                trace_file,
            ),
            patch.object(
                agent_fourday,
                "DATA_DIR",
                output_dir,
            ),
            patch.object(
                agent_fourday,
                "TRACE_FILE",
                trace_file,
            ),
            patch.object(
                agent_fourday,
                "generate_text",
                side_effect=fake_generate_text,
            ),
        ):
            for case in cases:
                try:
                    result = (
                        biomedical_agent.run_biomedical_agent(
                            task=case["task"],
                            max_chars=case.get(
                                "max_chars",
                                240,
                            ),
                            max_output_tokens=64,
                            max_output_chars=500,
                        )
                    )
                    reasons = evaluate_case(case, result)
                    actual = display_actual(result)
                except Exception as error:
                    reasons = [
                        "出现未捕获异常："
                        f"{type(error).__name__}: {error}"
                    ]
                    actual = "exception"

                passed = not reasons
                rows.append(
                    {
                        "id": case["id"],
                        "category": case["category"],
                        "passed": passed,
                        "actual": actual,
                        "reasons": reasons,
                    }
                )

                status = "PASS" if passed else "FAIL"
                print(
                    f"[{status}] {case['id']}: {actual}"
                )

                for reason in reasons:
                    print(f"       - {reason}")

    category_stats: dict[str, dict[str, int]] = {}

    for row in rows:
        category = row["category"]
        stats = category_stats.setdefault(
            category,
            {"total": 0, "passed": 0, "failed": 0},
        )
        stats["total"] += 1

        if row["passed"]:
            stats["passed"] += 1
        else:
            stats["failed"] += 1

    passed_count = sum(row["passed"] for row in rows)
    failed_rows = [row for row in rows if not row["passed"]]
    report = {
        "total": len(rows),
        "passed": passed_count,
        "failed": len(failed_rows),
        "pass_rate": round(
            passed_count / len(rows) * 100,
            1,
        ),
        "by_category": category_stats,
        "failed_cases": [
            {
                "id": row["id"],
                "actual": row["actual"],
                "reasons": row["reasons"],
            }
            for row in failed_rows
        ],
    }

    print("\n评测汇总：")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(1 if failed_rows else 0)


if __name__ == "__main__":
    main()