// import { json } from "stream/consumers";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  public status: number;
  public code?: string;
  public nextAction?: string;

  constructor(
    message: string,
    status: number,
    code?: string,
    nextAction?: string,
  ) {
    super(message);

    this.status = status;
    this.code = code;
    this.nextAction = nextAction;
  }
}

export async function apiFetch<T>(path:string,init:RequestInit={}):Promise<T>{
    const response = await fetch (`${API_URL}${path}`,{
        ...init,
        credentials:"include",
        headers:{
            ...(init.body instanceof FormData ? {} : {"Content-Type":"application/json"}),
            ...init.headers,
        },
    });
    if (!response.ok){
        const body = await response.json().catch(()=>null);
        const detail = body?.detail;
        throw new ApiError(
            detail?.message ?? `请求失败：${response.status}`,
            response.status,
            detail?.code,
            detail?.nextAction,
        );
    }
    if(response.status===204) return undefined as T;
    return response.json() as Promise<T>;
}

















//原本的next.js写法
// export type ChatEvent =
//   | { type: "run_started"; run_id?: string }
//   | { type: "status"; label: string }
//   | { type: "delta"; text: string }
//   | { type: "citation"; document_id: string; page: number | null; quote: string }
//   | { type: "done"; run_id: string; message_id?: string; latency_ms: number }
//   | { type: "error"; code?: string; message: string };

// export async function* streamChat(
//     conversationId:string,
//     message:string,
//     signal?:AbortSignal,
// ):AsyncGenerator<ChatEvent>{
//     const response = await fetch(
//         `${API_URL}/api/conversation/${conversationId}/messages:stream`,
//         {
//             method:"POST",
//             headers:{"Content-Type":"application/json"},
//             body:JSON.stringify({message}),
//             signal
//         },    
//     );

//     if (!response.ok || !response.body){
//         throw new Error(`流式请求失败：${response.status}`);
//     }

//     const reader = response.body.getReader();
//     const decoder = new TextDecoder();
//     let buffer = "";

//     while(true){
//         const {value,done} =await reader.read();
//         buffer += decoder.decode(value,{stream:!done});
//         const lines = buffer.split("\n");
//         buffer = lines.pop() ?? "";

//         for(const line of lines){
//             if (line.trim()) yield JSON.parse(line) as ChatEvent;
//         }
//         if(done) break;
//     }

//     if (buffer.trim()) yield JSON.parse(buffer) as ChatEvent;
// }


