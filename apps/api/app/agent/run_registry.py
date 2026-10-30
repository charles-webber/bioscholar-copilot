import asyncio
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ActiveRun:
    run_id: UUID
    owner_id: UUID
    cancel_event: asyncio.Event

class RunRegistry:
    def __init__(self) ->None:
        self._runs:dictp[UUID,ActiveRun]={}
        self._lock=asyncio.Lock()

    async def register(self,run_id:UUID,owner_id:UUID)->ActiveRun:
        async with self._lock:
            if run_id in self._runs:
                raise RuntimeError(f"run{run_id}已注册")
            active=ActiveRun(run_id,owner_id,asyncio.Event())
            self._runs[run_id]=active
            return active
    
    async def request_cancel(self,run_id:UUID,owner_id:UUID)->bool:
        async with self._lock:
            active=self._runs.get(run_id)
            if active is None or active.owner_id != owner_id:
                return False
            active.cancel_event.set()
            return True

    async def unregister(self,run_id:UUID)->None:
        async with self._lock:
            self._runs.pop(run_id,None)

    async def contains(self,run_id:UUID)->bool:
        async with self._lock:
            return run_id in self._runs

            