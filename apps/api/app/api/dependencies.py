from functools import lru_cache

from app.agent.bioagent_adapter import BioAgentAdapter
from app.agent.demo_bioagent import DemoAgentRuntime
from app.agent.runtime import AgentRuntime
from app.core.config import get_settings

@lru_cache
def get_agent_runtime()->AgentRuntime:
    settings = get_settings()

    if settings.agent_backend=="demo":
        return DemoAgentRuntime()

    return BioAgentAdapter()