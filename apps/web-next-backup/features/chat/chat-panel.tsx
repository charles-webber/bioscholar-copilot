"use client";
import { useState,type FormEvent } from "react";
import { sendMessage } from "@/lib/api/chat";


type UiMessage = {
    id:string;
    role:"user"|"assistant";
    content:string
};

export function ChatPanel(){
    const [messages,setMessages]=useState<UiMessage[]>([]);
    const [input,setInput]=useState("");
    const [conversationId, setConversationId] = useState<string>();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function handleSubmit(event: FormEvent<HTMLFormElement>){
        event.preventDefault();
        const message = input.trim();
        if (!message||isLoading) return;

        setMessages((current)=>[
            ...current,
            {
                id:crypto.randomUUID(),role:"user",content:message
            },
        ]
        );
        setInput("");
        setError(null);
        setIsLoading(true);

        try{
            const response = await sendMessage({
                message,
                conversation_id:conversationId,
            });
            setConversationId(response.conversation_id);
            setMessages((current)=>[
                ...current,
                {
                id: crypto.randomUUID(),
                role: "assistant",
                content: response.answer,
                },
            ]);
        }catch(caught){
            setError(caught instanceof Error ? caught.message:"发生未知错误");
        }finally{
            setIsLoading(false);
        }
    }

    return(
        <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-6 p-6">
            <header>
                <h1 className="text-2xl font-bold">BioScholar Copilot</h1>
                <p className="text-sm text-zinc-500">第 1 周：非流式聊天 MVP</p>
            </header>

            <section className="flex-1 space-y-3 rounded-xl border p-4">
                {
                    messages.length===0 &&(
                        <p className="text-zinc-500">输入一个生物学问题开始测试。</p>
                    )
                }
                {
                    messages.map((message)=>(
                        <article
                          key={message.id}
                          className={`rounded-lg p-3 ${
                            message.role==="user"?"bg-blue-50":"bg-zinc-100"
                          }`}
                        >
                            <strong>{message.role==="user"?"你":"BioAgent"}</strong>
                            <p className="whitespace-pre-wrap">{message.content}</p>
                          </article>
                    )
                )
                }
            </section>

            {
                error && (
                    <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-700">
                        {error}
                    </p>
                )
            }
            <form onSubmit={handleSubmit} className="flex gap-2">
                <input
                    aria-label="消息"
                    value={input}
                    onChange={(event)=>setInput(event.target.value)}
                    placeholder="例如：DNA 和 RNA 有什么区别？"
                    className="flex-1 rounded-lg border px-3 py-2"
                    />
                    <button
                        type="submit"
                        disabled={!input.trim()||isLoading}
                        className="rounded-lg bg-black px-4 py-2 text-white disabled:opacity-40"
                    >

                        发送
                    </button>
                </form>    
        </main>
    );
}
