
import { apiFetch } from "../../lib/api/client";
import type { ChatResponse, Conversation, Message } from "./types";

export const chatKeys = {
    all:["chat"] as const,
    conversations:()=>[...chatKeys.all,"conversations"] as const,
    messages:(conversationId:string)=>
        [...chatKeys.all, "messages", conversationId] as const,
}

export const chatApi = {
    listConversations:()=>apiFetch<Conversation[]>("/api/conversations"),
    createConversation : (title="新对话")=>
        apiFetch<Conversation>("/api/conversations",{
            method : "POST",
            body:JSON.stringify({title}),
        }),
    listMessages:(conversationId:string)=>
        apiFetch<Message[]>(`/api/conversations/${conversationId}/messages`),
    sendMessage:(conversationId:string,message:string)=>
        apiFetch<ChatResponse>(`/api/conversations/${conversationId}/messages`, {
            method:"POST",
            body:JSON.stringify({message}),
        }),
    deleteConversation:(conversationId:string)=>
        apiFetch<void>(`/api/conversations/${conversationId}`,{
            method:"DELETE",
        })    
};