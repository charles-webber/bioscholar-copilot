
import pytest

from app.agent.bioagent_adapter import BioAgentAdapter
from app.agent.runtime import AgentRuntimeError


def test_adapter_extracts_summary() -> None:
    def runner(*, task: str) -> dict:
        return {
            "ok": True,
            "summary": f"answer:{task}",
        }

    answer = BioAgentAdapter(runner).invoke("PCR 是什么？")

    assert answer.text == "answer:PCR 是什么？"
    assert answer.topic is None
    assert answer.source_refs == ()


def test_adapter_maps_structured_error() -> None:
    def runner(*, task: str) -> dict:
        return {
            "ok": False,
            "error": {
                "code": "BIOMEDICAL_TOPIC_NOT_FOUND",
                "message": "没有识别出主题。",
                "next_action": "请换一个主题。",
                "retryable": False,
            },
        }

    with pytest.raises(AgentRuntimeError) as captured:
        BioAgentAdapter(runner).invoke("unknown")

    assert captured.value.code == "BIOMEDICAL_TOPIC_NOT_FOUND"
    assert captured.value.message == "没有识别出主题。"
    assert captured.value.retryable is False


def test_adapter_rejects_malformed_success() -> None:
    def runner(*, task: str) -> dict:
        return {"ok": True}

    with pytest.raises(AgentRuntimeError) as captured:
        BioAgentAdapter(runner).invoke("PCR")

    assert captured.value.code == "BIOMEDICAL_INVALID_RESULT"
