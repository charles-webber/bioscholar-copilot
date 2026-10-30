import json 
from collections.abc import Mapping

def encode_sse(event:str,data:Mapping[str,object])->bytes:
    payload=json.dumps(data,ensure_ascii=False,separators=(",",":"))
    lines=[f"event:{event}"]
    lines.extend(f"data:{line}" for line in payload.splitlines() or [""])
    return ("\n".join(lines)+"\n\n").encode("utf-8")