import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agent_fourday
import biomedical_agent
import llm_client

class BiomedicalAgentTests(unittest.TestCase):
    def setUp(self)->None:
        self.temp_dir=tempfile.TemporaryDirectory()
        self.output_dir=Path(self.temp_dir.name)
        self.trace_file=self.output_dir/"trace.jsonl"
        self.summary_file=self.output_dir/"summaries.txt"

        self.patches=[
            patch.object(
                biomedical_agent,
                "BIO_OUTPUT_DIR",
                self.output_dir
            ),
            patch.object(
                biomedical_agent,
                "BIO_TRACE_FILE",
                self.trace_file
            ),
            patch.object(
                agent_fourday,
                "DATA_DIR",
                self.output_dir
            ),
            patch.object(
                agent_fourday,
                "TRACE_FILE",
                self.trace_file
            )

        ]

        for current_patch in self.patches:
            current_patch.start()

        agent_fourday._WRITTEN_KEYS.clear()

    def tearDown(self)->None:
        agent_fourday._WRITTEN_KEYS.clear()

        for current_patch in reversed(self.patches):
            current_patch.stop()

        self.temp_dir.cleanup()
    
    @staticmethod
    def fake_success(
        system_prompt:str,
        user_prompt:str,
        max_output_tokens:int,
    )->dict:
        return {
            "ok":True,
            "text":(
                "PCR 是扩增目标 DNA 片段的技术。\n\n"
                "证据来源：\n"
                "[来源: notes_long.txt | "
                "ref: note:PCR 聚合酶链式反应:cursor=0]"
            ),
            "model":"fake-model",
            "api_style":"chat_completion",
            "usage":{
                "prompt_tokens":10,
                "completion_tokens":5,
                "total_tokens":15,
            }
        }

    def read_trace(self)->list[dict]:
        lines=self.trace_file.read_text(
            encoding="utf-8"
        ).splitlines()
        return [json.loads(line) for line in lines]
    
    def test_normal_knowledge_question(self)->None:
        with patch.object(
            agent_fourday,
            "generate_text",
            side_effect=self.fake_success,
            )as model_call:
            result=biomedical_agent.run_biomedical_agent(
                "PCR是什么？",
                max_output_tokens=64,
                max_output_chars=1000
            )

        self.assertTrue(result["ok"])
        self.assertIn("PCR", result["resolved_topic"])
        self.assertIn("证据来源", result["summary"])
        self.assertTrue(self.summary_file.exists())
        model_call.assert_called_once()

        generate_records=[
            record
            for record in self.read_trace()
            if record.get("tools")=="generate_text"
        ]
        self.assertEqual(len(generate_records),1)
        self.assertEqual(
            generate_records[0]["observation"]["usage"]["total_tokens"],
            15
        )

    def  test_unknown_topic_stops_before_model(self)->None:
        with patch.object(
            agent_fourday,
            "generate_text"
        )as model_call:
            result=biomedical_agent.run_biomedical_agent(
                "量子纠缠是什么？"
            )
        
        self.assertFalse(result["ok"])
        self.assertEqual(
            result["error"]["code"],
            "BIOMEDICAL_TOPIC_NOT_FOUND"
        )
        model_call.assert_not_called()
        self.assertFalse(self.summary_file.exists())
        
    def test_high_risk_request_stops_before_model(self) -> None:
        with patch.object(
            agent_fourday,
            "generate_text",
        ) as model_call:
            result = biomedical_agent.run_biomedical_agent(
                "帮我诊断我是不是得了癌症"
            )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["error"]["code"],
            "BIOMEDICAL_POLICY_BLOCKED",
        )
        model_call.assert_not_called()
        self.assertFalse(self.summary_file.exists())

    def test_model_timeout_does_not_write_summary(self) -> None:
        fake_timeout = {
            "ok": False,
            "error": {
                "code": "LLM_TIMEOUT",
                "message": "模型请求超时。",
                "retryable": True,
            },
        }

        with patch.object(
            agent_fourday,
            "generate_text",
            return_value=fake_timeout,
        ):
            result = biomedical_agent.run_biomedical_agent(
                "PCR 是什么？"
            )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["error"]["code"],
            "LLM_TIMEOUT",
        )
        self.assertFalse(self.summary_file.exists())


    def test_empty_model_response_is_rejected(self) -> None:
        fake_settings = {
            "api_key": "fake-key",
            "base_url": "https://invalid.example/v1",
            "model_id": "fake-model",
            "api_style": "chat_completions",
        }

        with (
            patch.object(
                llm_client,
                "_load_settings",
                return_value=fake_settings,
            ),
            patch.object(
                llm_client,
                "OpenAI",
                return_value=object(),
            ),
            patch.object(
                llm_client,
                "_request_text",
                return_value=("", None),
            ),
        ):
            result = llm_client.generate_text(
                system_prompt="只做测试。",
                user_prompt="只做测试。",
                max_output_tokens=32,
            )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["error"]["code"],
            "LLM_EMPTY_RESPONSE",
        )

    def test_unsafe_model_output_is_not_saved(self) -> None:
        unsafe_result = self.fake_success("", "", 64)
        unsafe_result["text"] = "你应该停药"

        with patch.object(
            agent_fourday,
            "generate_text",
            return_value=unsafe_result,
        ):
            result = biomedical_agent.run_biomedical_agent(
                "PCR 是什么？"
            )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["error"]["code"],
            "MODEL_OUTPUT_BLOCKED",
        )
        self.assertFalse(self.summary_file.exists())

    def test_uncertainty_answer_is_allowed(self) -> None:
        uncertain_result = self.fake_success("", "", 64)
        uncertain_result["text"] = (
            "根据当前本地证据，无法确定。\n\n"
            "证据来源：\n"
            "[来源: notes_long.txt | "
            "ref: note:PCR 聚合酶链式反应:cursor=0]"
        )

        with patch.object(
            agent_fourday,
            "generate_text",
            return_value=uncertain_result,
        ):
            result = biomedical_agent.run_biomedical_agent(
                "PCR 的精确退火温度是多少？"
            )

        self.assertTrue(result["ok"])
        self.assertIn(
            "根据当前本地证据，无法确定。",
            result["summary"],
        )
    def test_saved_output_has_character_limit(self) -> None:
        long_result = self.fake_success("", "", 64)
        long_result["text"] = "A" * 500

        with patch.object(
            agent_fourday,
            "generate_text",
            return_value=long_result,
        ):
            result = biomedical_agent.run_biomedical_agent(
                "PCR 是什么？",
                max_output_chars=100,
            )

        self.assertTrue(result["ok"])
        self.assertTrue(
            result["summary"].endswith("...[truncated]")
        )
        self.assertLessEqual(len(result["summary"]), 114)


if __name__ == "__main__":
    unittest.main()