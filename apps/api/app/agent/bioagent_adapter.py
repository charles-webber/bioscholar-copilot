import asyncio

class BioAgentAdapter:
    def __init__(self,bioagent):
        self.bioagent=bioagent

    async def invoke(self,message:str)->str:
        return await asyncio.to_thread(self.bioagent.run,message)
