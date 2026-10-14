import os 
from typing import Any
from dotenv import load_dotenv
from pathlib import Path

API_ENV_FILE=Path(__file__).resolve().parents[3]/".env"
load_dotenv(API_ENV_FILE)

from openai import(
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

ALLOWED_API_STYLES={"chat_completions","responses"}
DEFAULT_TIMEOUT_SECONDS=20.0
DEFAULT_MAX_OUTPUT_TOKENS=512

def _error(
    code:str,
    message:str,
    retryable:bool,
)->dict[str,Any]:
    """生成统一的失败返回值。"""
    return {
        "ok":False,
        "error":{
            "code":code,
            "message":message,
            "retryable":retryable
        },
        
    }

def _require_env(name:str)->str:
    """读取必需的环境变量。"""
    value=os.getenv(name,"").strip()

    if not value:
        raise RuntimeError(f"缺少环境变量:{name}")
    return value

def _load_settings()->dict[str,str]:
    """集中读取并校验模型连接配置。"""
    api_style=_require_env("BIOMEDICAL_LLM_API_STYLE").lower()

    if api_style not in ALLOWED_API_STYLES:
        allowed=",".join(sorted(ALLOWED_API_STYLES))
        raise RuntimeError(
            f"BIOMEDICAL_LLM_API_STYLE 只能填写：{allowed}"
        )

    return {
        "api_key":_require_env("BIOMEDICAL_LLM_API_KEY"),
        "base_url":_require_env("BIOMEDICAL_LLM_BASE_URL"),
        "model_id":_require_env("BIOMEDICAL_LLM_MODEL"),
        "api_style":api_style,
    }

def _usage_to_dict(usage:Any)->dict[str,Any]|None:
    """把不同接口的 token 用量转换成普通字典。"""
    if usage is None:
        return None

    if isinstance(usage,dict):
        return usage

    model_dump=getattr(usage,"model_dump",None)

    if callable(model_dump):
        return model_dump()

    return {"value":str(usage)}


def _request_text(
    client:OpenAI,
    model_id:str,
    api_style:str,
    system_prompt:str,
    user_prompt:str,
    max_output_tokens:int,
)->tuple[str,dict[str,Any]|None]:
    """按照配置的接口格式请求文本。"""
    if api_style=="chat_completions":
        response=client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role":"system",
                    "content":system_prompt,
                },
                {
                    "role":"user",
                    "content":user_prompt,
                }
            ],
            max_tokens=max_output_tokens,
        )
        text=response.choices[0].message.content or ""
        usage=_usage_to_dict(response.usage)
        return text,usage

    response = client.responses.create(
        model=model_id,
        instructions=system_prompt,
        input=user_prompt,
        max_output_tokens=max_output_tokens,
    )
    text=response.output_text or ""
    usage = _usage_to_dict(response.usage)
    return text,usage

def generate_text(
    system_prompt:str,
    user_prompt:str,
    max_output_tokens:int = DEFAULT_MAX_OUTPUT_TOKENS,
)->dict[str,Any]:
    """调用模型并返回统一的成功或失败字典。"""
    if not isinstance(system_prompt,str) or not system_prompt.strip():
        return _error(
            code="LLM_INVALID_INPUT",
            message="system_prompt不能为空",
            retryable=False,
        )
    if not isinstance(user_prompt,str) or not user_prompt.strip():
        return _error(
            code="LLM_INVALID_INPUT",
            message="user_prompt不能为空",
            retryable=False,
        )
    if (
        not isinstance(max_output_tokens,int)
        or not 1<=max_output_tokens<=1024
    ):return _error(
        code="LLM_INVALID_INPUT",
        message="max_output_tokens必须是1到1024的整数",
        retryable=False,
    )

    try:
        settings = _load_settings()

        client=OpenAI(
            api_key=settings["api_key"],
            base_url=settings["base_url"],
            timeout=DEFAULT_TIMEOUT_SECONDS,  
            max_retries=1,      
        )

        text,usage=_request_text(
            client=client,
            model_id=settings["model_id"],
            api_style=settings["api_style"],
            system_prompt=system_prompt.strip(),
            user_prompt=user_prompt.strip(),
            max_output_tokens=max_output_tokens,
        )

    except RuntimeError as error:
        return _error(
            code="LLM_CONFIG_ERROR",
            message=str(error),
            retryable=False,
        )

    except AuthenticationError:
        return _error(
            code="LLM_AUTH_FAILED",
            message="模型认证失败，请检查 API Key 和认证方式。",
            retryable=False,
        )

    except RateLimitError:
        return _error(
            code="LLM_RATE_LIMITED",
            message="模型请求受限，请检查频率、并发、余额和渠道限流。",
            retryable=True,
        )

    except APITimeoutError:
        return _error(
            code="LLM_TIMEOUT",
            message="模型请求超时。",
            retryable=True,
        )

    except APIConnectionError:
        return _error(
            code="LLM_CONNECTION_ERROR",
            message="无法连接模型接口，请检查网络、代理和 Base URL。",
            retryable=True,
        )
    
    except APIStatusError as error:
        retryable=(
            error.status_code in {408,409,429}
            or error.status_code>=500
        )
        return _error(
            code=f"LLM_HTTP_{error.status_code}",
            message=(
                f"模型接口返回HTTP{error.status_code}"
                f"{str(error)[:300]}"
            ),
            retryable=retryable,
        )
    
    except (AttributeError,IndexError,TypeError) as error:
        return _error(
            code="LLM_INVALID_RESPONSE",
            message=f"模型返回格式无法解析:{error}",
            retryable=False,
        )
    
    text=text.strip()

    if not text:
        return _error(
            code="LLM_EMPTY_RESPONSE",
            message="模型调用成功，但是回答内容为空",
            retryable=True,
        )
    
    return {
        "ok":True,
        "text":text,
        "model":settings["model_id"],
        "api_style":settings["api_style"],
        "usage":usage,
    }