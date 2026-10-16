import { json } from "stream/consumers";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ChatEvent =
  | { type: "run_started"; run_id?: string }
  | { type: "status"; label: string }
  | { type: "delta"; text: string }
  | { type: "citation"; document_id: string; page: number | null; quote: string }
  | { type: "done"; run_id: string; message_id?: string; latency_ms: number }
  | { type: "error"; code?: string; message: string };

export async function* streamChat(
    conversationId:string,
    message:string,
    signal?:AbortSignal,
):AsyncGenerator<ChatEvent>{
    const response = await fetch(
        `${API_URL}/api/conversation/${conversationId}/messages:stream`,
        {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({message}),
            signal
        },    
    );

    if (!response.ok || !response.body){
        throw new Error(`流式请求失败：${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while(true){
        const {value,done} =await reader.read();
        buffer += decoder.decode(value,{stream:!done});
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for(const line of lines){
            if (line.trim()) yield JSON.parse(line) as ChatEvent;
        }
        if(done) break;
    }

    if (buffer.trim()) yield JSON.parse(buffer) as ChatEvent;
}


