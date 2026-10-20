
import { apiFetch } from "../../lib/api/client";
import type { ChatResponse } from "./types";

export type Conversation = {
    id : string,
    title : string,
    created_at : string,
    update_at : string  
};

export type Message = {
    id: string;
    role: "user" | "assistant";
    content: string;
    status: string;
    created_at: string;

};

export const chatApi = {
    listConversations:()=>apiFetch<Conversation[]>("/api/conversations"),
    createConversation : (title:string)=>
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
};