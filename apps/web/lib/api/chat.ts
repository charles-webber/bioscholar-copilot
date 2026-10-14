export type ChatRequest={
    message:string;
    conversation_id?:string;
};

export type ChatResponse={
    conversation_id: string;
    answer: string;
    citations: Array<{
    document_id: string;
    title: string;
    page: number | null;
    quote: string;
}>;
    finish_reason:"stop"|"length"|"error";
};

const API_URL=process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function sendMessage(input:ChatRequest):Promise<ChatResponse>
{
    const response=await fetch(
        `${API_URL}/api/chat`, 
        {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(input),
    }
    );

    if(!response.ok){
        let message=`请求失败：${response.status}`;
        try{
            const body = (await response.json()) as {detail?:string};
            if (body.detail) message=body.detail;
        }catch{
            // 响应不是 JSON 时保留包含状态码的默认错误。
        }
        throw new Error(message);
    }
    return response.json() as Promise<ChatResponse>;
}
