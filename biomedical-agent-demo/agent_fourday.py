import hashlib
import json
from pathlib import Path
import time
from typing import Any

from biomedical_policy import check_model_output 
from context_builder import (
    build_context,
    build_evidence,
    build_system_prompt,
    build_user_prompt,
    load_recent_trace,
)
from llm_client import generate_text
_WRITTEN_KEYS:set[str]=set()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TRACE_FILE=BASE_DIR/"outputs"/"trace.jsonl"

def _load_default_notes()->dict[str,str]:
    """读取默认的 ### 标题格式知识库。"""
    notes_file=DATA_DIR/"notes_long.txt"
    text=notes_file.read_text(encoding="utf-8")
    notes:dict[str,str]={}

    for block in text.split("###"):
        block=block.strip()
        if not block:
            continue
        lines=block.splitlines()
        title=lines[0].strip()
        content="\n".join(lines[1:]).strip()

        if title:
            notes[title]=content
    return notes

NOTES=_load_default_notes()

#这种带大括号的是字典dict啊

#接下来我们写一些agent可以调用的工具
def search_notes(query:str)->dict[str,Any]:
    for title,content in NOTES.items():#这里搞一个循环
        if title.lower() in query.lower():
            return {
                "ok":True,
                "title":title,
                "content":content.strip()
            }
    return {
        "ok":False,
        "error":f"没有找到和'{query}'相关的笔记"
    }

def write_summary(text:str)->dict[str,Any]:
#把已通过安全检查的总结追加到本地文件。
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    outputs_file=DATA_DIR /"summaries.txt"

    with outputs_file.open(
        "a",
        encoding="utf-8"
    )as f:

        f.write(text)
        f.write("\n\n")
    
    return {
        "ok":True,
        "file":str(outputs_file)

    }

#最后要开始写一写trace，相当于agent的日志了
#所谓的jsonl 全称是json lines，把py的dict从列转成行了，一行是一个json对象
TRACE_FILE=BASE_DIR/"outputs"/"trace.jsonl"

def write_trace(
    step:int,
    thought_summary:str,
    tools:str,
    #ARGS指的是arguments
    args:dict[str,Any],
    observation:dict[str,Any],
    cost_estimate:float=0.0
)->None:
    """记录可审计的步骤摘要，不记录私密思维过程。"""
    record={
        "step":step,
        "thought_summary":thought_summary,
        "tools":tools,
        "args":args,
        "observation":observation,
        "cost_estimate":cost_estimate
    }

    TRACE_FILE.parent.mkdir(parents=True,exist_ok=True)

    with TRACE_FILE.open(
        "a",
        encoding="utf-8"
    )as f:
        f.write(
            json.dumps(
                record,
                ensure_ascii=False
        )
        +"\n"
    )

#!这块是新增的工具,首先是报错提示
def tool_error(
    code:str,
    message:str,
    next_action:str,
    retryable:bool=False
    )->dict[str,Any]:
    """生成统一的核心流程错误。"""
    return{
        "ok":False,
        "error":{
            "code":code,
            "message":message,
            "next_action":next_action,
            "retryable":retryable
        }
    }

#!然后是分页搜索功能
def search_notes_page(
    query:str,
    page:int=1,
    page_size:int=2,
    response_format:str="concise"
    ):
    #agent 使用的分页搜索
    """分页搜索知识库标题。"""
    if page<1 or not 1<=page_size<=3:
        return tool_error(
            code="INVALID_ARGUMENT",
            message="page必须大于0，page_size必须在1到3之间",
            next_action="使用page=1,page=2之后重试"
        )
    if response_format not in ("concise","detailed"):
        return tool_error(
            code="INVALID_ARGUMENT",
            message="response_format 只能是 concise 或 detailed。",
            next_action="普通搜索用 concise；需要继续读取时用 detailed。",
        )
    normalized_query=query.strip().lower()
    matches=[
        (title,content)
        for title,content in NOTES.items()
        if normalized_query in title.lower()
    ]
    if not matches:
        return tool_error(
              "NOT_FOUND",
            f"没有找到和{query}相关的笔记",
            f"换一个主题；可用:{','.join(NOTES)}"
        )

    start=(page-1)*page_size
    current=matches[start:start+page_size]
    result=[]
    for title,content in current:
        item={
            "title":title,
            "snippet":" ".join(content.split())[:120], 
        }
        if response_format=="detailed":
            item["note_ref"]=title
        result.append(item)
#!三元表达式，中间是判断条件，符合走左边，不符合就走右边
    next_page=page+1 if start +page_size<len(matches)else None
    return {
        "ok":True,
        "result":result,
        "next_page":next_page,
    }
    
#!按需读取一段笔记
def get_note_chunk(
    note_ref:str,
    cursor:int=0,
    max_chars:int=240)->dict[str,Any]:
    if note_ref not in NOTES:
        return tool_error(
            code="NOT_FOUND",
            message=f"找不到笔记“{note_ref}”。",
            next_action="先调用 search_notes_page(..., response_format='detailed')。",
        )
    if cursor<0 or not 80<=max_chars<=600:
        return tool_error(
            code="INVALID_ARGUMENT",
            message="cursor 不能小于 0，max_chars 必须在 80 到 600 之间。",
            next_action="先用 cursor=0、max_chars=240。",
        )
    content=NOTES[note_ref].strip()
    chunk=content[cursor:cursor+max_chars]
    next_cursor=cursor+len(chunk)
    return {
        "ok":True,
        "title":note_ref,
        "content":chunk,
        "truncated":next_cursor<len(content),
        "next_cursor":(
            next_cursor if next_cursor<len(content) else None
        )
    }
#!查询timeout工具
def call_read_tool(
    tool,
    args:dict[str,Any],
    timeout_ms:int=1000,
    retries:int=2
    )->dict[str,Any]:   
    """为本地只读工具增加超时判断和有限重试。"""
    result:dict[str,Any]
    for attempt in range (retries+1):
        started=time.perf_counter()
        try:
            result=tool(**args)
        except Exception as error:
            result=tool_error(
                code="TEMPORARY_UNAVAILABLE",
                message=f"工具执行失败：{error}",
                next_action="稍后重试；若持续失败，检查工具参数。",
                retryable=True
            )

        elapsed_ms=(time.perf_counter()-started)*1000
        if elapsed_ms>timeout_ms:
            result=tool_error(
            code="TIMEOUT",
            message=f"工具超过 {timeout_ms} ms。",
            next_action="缩小查询范围或减少 max_chars 后重试。",
            retryable=True,

            )    

        if result["ok"] or not result["error"]["retryable"]:
            return result
        if attempt <retries:
            time.sleep(0.2*(attempt+1))

    return result

#!防止重复写入
def write_summary_once(
    text:str,
    idempotency_key:str
    )->dict[str,Any]:

    if idempotency_key in _WRITTEN_KEYS:
        return {
            "ok":True,
            "file":str(DATA_DIR/"summaries.txt"),
            "replayed":True,            
        }

    try:
        result=write_summary(text)
    except OSError as error:
        return tool_error(
            code="TEMPORARY_UNAVAILABLE",
            message=f"写入失败：{error}",
            next_action="检查目录权限后，用相同的 idempotency_key 重试。",  
            retryable=True
        )

    if result["ok"]:
        _WRITTEN_KEYS.add(idempotency_key)
    return result

#!这里是接入模型之后需要的新函数
def _limit_output(text:str,max_chars:int)->str:
    """对模型输出再做一次字符长度限制。"""
    cleaned=text.strip()

    if len(cleaned)<=max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip()+"...[truncated]"

def _llm_trace_observation(result:dict[str,Any])->dict[str,Any]:
    """为 trace 保留状态和用量，不保存完整模型回答。"""
    if not result["ok"]:
        return{
            "ok":False,
            "error":result["error"],
        }

    return{
        "ok":True,
        "model":result["model"],
        "api_style":result["api_style"],
        "usage":result["usage"],
        "text_chars":len(result["text"])
    }


#*接下来是最核心的代码
def run_agent(
    topic:str,
    user_task:str|None=None,
    max_step:int=5,
    max_chars:int=240,
    max_output_tokens:int=512,
    max_output_chars:int=1200,
    )->dict[str,Any]:
    """检索本地证据，调用模型，检查输出并写入总结。"""

    if max_step<5:
        return tool_error(
            code="MAX_STEPS_TOO_SMALL",
            message="当前流程至少需要五个步骤。",
            next_action="把 max_step 设置为 5 或更大。",
        )

    if not 100<=max_output_chars<=4000:
        return tool_error(
            code="INVALID_ARGUMENT",
            message="max_output_chars必须在 100 到 4000 之间。",
            next_action="先使用 max_output_chars=1200。",
        )
    question = (user_task or topic).strip()

    search_result=call_read_tool(
        search_notes_page,
        {
            "query":topic,
            "response_format":"detailed"
        }
    )

    write_trace(
        step=1,
        thought_summary="先根据标准主题搜索本地知识库。",
        tools="search_notes_page",
        args={"query":topic},
        observation=search_result,
    )

    if not search_result["ok"]:
        return search_result

    note_ref = search_result["result"][0]["note_ref"]

    read_result=call_read_tool(
        get_note_chunk,
        {
            "note_ref":note_ref,
            "cursor":0,
            "max_chars":max_chars
        }
    )    

    write_trace(
        step=2,
        thought_summary="读取生成回答所需的受限知识片段。",
        tools="get_note_chunk",
        args={
            "note_ref":note_ref,
            "cursor":0,
            "max_chars":max_chars,
        },
        observation={
            "ok":read_result["ok"],
            "title":read_result.get("title"),
            "truncated":read_result.get("truncated"),
            "next_cursor":read_result.get("next_cursor"),
            "error":read_result.get("error"),
        },  
    )
    if not read_result["ok"]:
        return read_result

    evidence=build_evidence(
        ref=f"note:{note_ref}:cursor=0",
        title=note_ref,
        content=read_result["content"],
        source="notes_long.txt",
        cursor=0,
        max_chars=max_chars
    )

    system_instruction=build_system_prompt()

    context=build_context(
        system=system_instruction,
        task=question,
        memory={
            "resolved_topic":topic,
            "note_ref":note_ref,
        },
        retrieved_evidence=[evidence],
        recent_trace=load_recent_trace(
            TRACE_FILE,
            max_items=3,
        ),
    )

    llm_result=generate_text(
        system_prompt=system_instruction,
        user_prompt=build_user_prompt(context),
        max_output_tokens=max_output_tokens,
    )
     
    write_trace(
        step=3,
        thought_summary="把原问题和本地证据交给统一模型调用层。",
        tools="generate_text",
        args={
            "topic":topic,
            "max_output_tokens":max_output_tokens,
        },
        observation=_llm_trace_observation(llm_result),
    )

    if not llm_result["ok"]:
        error=llm_result["error"]
        return tool_error(
            code=error["code"],
            message=error["message"],
            next_action="检查模型配置或稍后重试；不要写入空总结。",
            retryable=error["retryable"]
        )
    
    raw_summary=llm_result["text"]
    output_policy=check_model_output(raw_summary)

    write_trace(
        step=4,
        thought_summary="保存前检查模型输出的安全边界。",
        tools="check_model_output",
        args={"text_chars":len(raw_summary)},
        observation={
            "ok":output_policy.allowed,
            "reason":output_policy.reason,
            "next_action":output_policy.next_action,
        },
    )

    if not output_policy.allowed:
        return tool_error(
            code="MODEL_OUTPUT_BLOCKED",
            message=output_policy.reason,
            next_action=output_policy.next_action,
            retryable=False
        )
    
    summary=_limit_output(raw_summary,max_output_chars)
    task_hash=hashlib.sha256(
        question.encode("utf-8")
    ).hexdigest()[:12]
    idempotency_key=f"summary-{topic.casefold()}-{task_hash}"
    write_result=write_summary_once(
        summary,
        idempotency_key,
    )

    write_trace(
        step=5,
        thought_summary="安全检查通过后写入受限长度的总结。",
        tools="write_summary_once",
        args={
            "idempotency_key":idempotency_key,
            "text_chars":len(summary),
        },
        observation=write_result
    )

    if not write_result["ok"]:
        return write_result
    
    return{
        "ok":True,
        "file":write_result["file"],
        "summary":summary,
        "context":context,
        "llm":{
            "model":llm_result["model"],
            "api_style":llm_result["api_style"],
            "usage":llm_result["usage"],
        }
    }


