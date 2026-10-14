from pathlib import Path
from biomedical_config import NOTES_FILE,TOPIC_ALIASES

def load_notes(path:Path=NOTES_FILE)->dict[str,str]:
    """读取 ### 标题格式的知识库。"""
    text=path.read_text(encoding="utf-8")
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

def find_title_for_target(
    target:str,
    notes:dict[str,str]
)->str|None:
    """把别名对应的目标名映射到真实知识库标题。"""
    target_lower=target.casefold()

    for title in notes:
        if title.casefold()==target_lower:
            return title

    for title in notes:
        title_lower=title.casefold()
        
        if title_lower.startswith(f"{target_lower}"):
            return title

    for title in notes:
        if target_lower in title.casefold():
            return title
    
    return None




def resolve_topic(task:str,notes:dict[str,str])->str|None:
    """把自然语言任务解析为知识库中的主题标题。"""
    normalized = task.strip().lower()

    if not normalized:
        return None

    for title in notes:
        if normalized == title.casefold():
            return title

    #! 长别名优先，避免“免疫”先于“免疫学”命中。
    aliases=sorted(TOPIC_ALIASES.items(),key=lambda item:len(item[0]),reverse=True)

    for alias,target in aliases:
        if alias.casefold() not in normalized:
            continue

        title=find_title_for_target(target,notes)

        if title is not None:
            return title
    #列表解析式
    complete_title_mentions=[
        title
        for title in notes
        if title.casefold() in normalized
    ]

    if complete_title_mentions:
        return max(complete_title_mentions,key=len)
    
    partial_title_matches=[
        title
        for title in notes
        if normalized in title.casefold()
    ]

    if partial_title_matches:
        return min(partial_title_matches,key=len)

    return None

def list_topics(notes:dict[str,str])->list[str]:
    """返回可用主题，便于错误提示或前端展示。"""
    return sorted(notes)