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

export async function sendMessage(input:ChatRequest):Promise<ChatResponse>{
    const response=await fetch(
        `${API_URL}/api/chat`, 
        {
        method:"POST",
        headers:{"Content-Type":"application"},
        body:JSON.stringify(input),
    }
    );

    if(!response.ok){
        throw new Error(`请求失败：${response.status}`);
    }
    return response.json() as Promise<ChatResponse>;
}
