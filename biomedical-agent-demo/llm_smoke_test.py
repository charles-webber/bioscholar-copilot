import sys

from llm_client import generate_text

def main()->int:
    """验证统一调用层能返回结构化结果。"""
    result=generate_text(
        system_prompt="你是一个连接测试助手。",
        user_prompt="请只回复：调用层连接成功",
        max_output_tokens=512,
    )
    if not result["ok"]:
        error=result["error"]
        print(
            f"{error['code']}:{error['message']}",
            file=sys.stderr,
        )
        print(
        f"retryable={error['retryable']}",
        file=sys.stderr,  
        )
        return 1


    print(f"模型返回：{result['text']}")
    print(f"模型 ID：{result['model']}")
    print(f"接口类型：{result['api_style']}")

    if result["usage"] is not None:
        print(f"Token 用量:{result['usage']}")
    return 0    
if __name__ == "__main__":
    raise SystemExit(main())    