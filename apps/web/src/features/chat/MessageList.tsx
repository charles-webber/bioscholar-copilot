import type { Message } from "./api";

export function MessageList({ messages }:{messages : Message[]}){
    if (messages.length===0) return <p>开始你的第一个问题.</p>;
    return (
    <ol aria-live ="polite">
        {messages.map((message)=>(
            <li key={message.id} data-role={message.role}>
                <strong>{message.role==="user"?"你":"BioScholar"}</strong>
                <p>{message.content}</p>
            </li>    
        ))}
    </ol>
    )
}