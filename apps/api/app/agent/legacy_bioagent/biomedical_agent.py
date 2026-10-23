import argparse
import json
from typing import Any

from .import agent_fourday as core 

from .biomedical_config import BIO_OUTPUT_DIR, BIO_TRACE_FILE
from .biomedical_kb import list_topics, load_notes, resolve_topic
from .biomedical_policy import check_request

def configure_core()->dict[str,str]:
    """把核心 Agent 的模块级知识库替换为生物医学知识库。"""
    notes = load_notes()
    #! run_agent() 内部会读取 agent_fourday.NOTES。
    core.NOTES=notes

    #! 原 write_summary() 会根据 DATA_DIR 拼接 summaries.txt。
    BIO_OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
    core.DATA_DIR=BIO_OUTPUT_DIR
    core.TRACE_FILE=BIO_TRACE_FILE
    core._WRITTEN_KEYS.clear()

    return notes

def safe_error(
    code:str,
    message:str,
    next_action:str
    )->dict[str,Any]:
    return{
        "ok":False,
        "error":{
            "code":code,
            "message":message,
            "next_action":next_action,
            "retryable":False
        }
    }

def run_biomedical_agent(
    task:str,
    max_chars:int=240,
    max_output_tokens:int =2048,
    max_output_chars:int = 1200,
    )->dict[str,Any]:
    """执行安全检查、主题解析、本地检索和模型回答。"""


    policy=check_request(task)
    if not policy.allowed:
        return safe_error(
            code="BIOMEDICAL_POLICY_BLOCKED",
            message=policy.reason,
            next_action=policy.next_action
        )
    notes=configure_core()
    topic=resolve_topic(task,notes)

    if topic is None:
        available_topics=", ".join(list_topics(notes)[:12])
        return safe_error(
            code="BIOMEDICAL_TOPIC_NOT_FOUND",
            message="没有识别出知识库中的生物医学主题。",
            next_action=f"请尝试使用具体主题，例如：{available_topics}"
        )
    
    #! 关键：把标准主题传给原函数，不把长自然语言直接传进去。
    result =core.run_agent(
        topic=topic,
        user_task=task,
        max_output_chars=max_output_chars,
        max_output_tokens=max_output_tokens,
        max_chars=max_chars
        )
    result["user_task"]=task
    result["resolved_topic"]=topic
    return result

def main()->None:
    parser=argparse.ArgumentParser(
        description="基于本地证据和大模型的生物医学学习 Agent"
        )
    parser.add_argument(
        "task",
        help="生物医学问题，例如：PCR 是什么？"
        )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=240,
        help="发送给模型的单段证据最大字符数.",
        )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=2048,
        help="模型最大输出 token 数。",
        )
    parser.add_argument(
        "--max-output-chars",
        type=int,
        default=1200,
        help="保存和返回的最大字符数。",
        )
    args=parser.parse_args()

    result=run_biomedical_agent(
        task=args.task,
        max_chars=args.max_chars,
        max_output_tokens=args.max_output_tokens,
        max_output_chars=args.max_output_chars
        )
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__ =="__main__":
    main()
