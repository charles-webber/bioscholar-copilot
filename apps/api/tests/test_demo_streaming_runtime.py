
import asyncio
from uuid import uuid4

import pytest

from app.agent.demo_streaming import DemoStreamingRuntime
from app.agent.streaming_runtime import AgentGenerationCancelled


def test_normal_stream():
    """测试正常流式输出"""

    async def run():
        runtime = DemoStreamingRuntime()
        run_id = uuid4()
        cancel_event = asyncio.Event()

        events = []

        async for event in runtime.stream(
            message="什么是RAG？",
            run_id=run_id,
            cancel_event=cancel_event,
        ):
            events.append(event)
            print(event.to_dict())

        assert len(events) == 2
        assert events[0].type == "run_started"
        assert events[1].type == "text_delta"
        assert "什么是RAG？" in events[1].text

    asyncio.run(run())


def test_cancel_stream():
    """测试取消流式生成"""

    async def run():
        runtime = DemoStreamingRuntime()
        run_id = uuid4()
        cancel_event = asyncio.Event()

        stream = runtime.stream(
            message="什么是RAG？",
            run_id=run_id,
            cancel_event=cancel_event,
        )

        # 先获取第一个事件
        first = await anext(stream)
        assert first.type == "run_started"

        # 模拟用户点击停止
        cancel_event.set()

        # 再次读取时应抛出取消异常
        with pytest.raises(AgentGenerationCancelled):
            await anext(stream)

        await stream.aclose()

    asyncio.run(run())
