import json
import threading
import time
from typing import Any

import httpx


API_URL = "http://localhost:8000"


def create_conversation() -> str:
    response = httpx.post(f"{API_URL}/api/conversations", timeout=10)
    response.raise_for_status()
    return str(response.json()["id"])


def main() -> None:
    conversation_id = create_conversation()
    run_id: str | None = None

    with httpx.stream(
        "POST",
        f"{API_URL}/api/conversations/{conversation_id}/messages:stream",
        json={"message": "PCR 是什么？"},
        timeout=30,
    ) as response:
        print("状态码:", response.status_code)
        if response.status_code >= 400:
            response.read()
            print("错误详情:", response.text)
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith("data:"):
                continue
            event: dict[str, Any] = json.loads(line[5:].lstrip())
            print(event)
            if event["type"] == "run_started":
                run_id = str(event["run_id"])

                def cancel() -> None:
                    time.sleep(0.1)
                    result = httpx.post(
                        f"{API_URL}/api/runs/{run_id}/cancel",
                        timeout=10,
                    )
                    result.raise_for_status()
                    print("cancel:", result.json())

                threading.Thread(target=cancel, daemon=True).start()
            if event["type"] in {"run_completed", "run_cancelled", "run_error"}:
                break

    if run_id is None:
        raise RuntimeError("没有收到 run_started")


if __name__ == "__main__":
    main()