import { useState } from "react";
import { useMutation,useQuery,useQueryClient } from "@tanstack/react-query";
import { ApiError } from "../../lib/api/client";
import { chatApi } from "./api";
import { Composer } from "./Composer";
import { ConversationList } from "./ConversationList";
import { MessageList } from "./MessageList";

export function ChatPage(){
  const queryClient = useQueryClient();
  const [selectedId,setSelectedId] = useState<string|null>(null);
  const [error,setError]= useState("");

  const conversations = useQuery({
    queryKey:["conversations"],
    queryFn:chatApi.listConversations,
  });
  const messages = useQuery({
    queryKey:["messages",selectedId],
    queryFn:()=>chatApi.listMessages(selectedId!),
    enabled:selectedId !== null,
  });
  const createConversation = useMutation({
    mutationFn:()=>chatApi.createConversation("新对话"),
    onSuccess:async (created)=>{
      setSelectedId(created.id);
      await queryClient.invalidateQueries({queryKey:["conversations"]});

    },
  });
  const sendMessage=useMutation({
    mutationFn:({id,text}:{id:string;text:string})=>chatApi.sendMessage(id,text),
    onSuccess:async(_result,variables)=>{
      await Promise.all([
        queryClient.invalidateQueries({queryKey:["messages",variables.id]}),
        queryClient.invalidateQueries({queryKey:["conversations"]}),
      ]);
    },
  });

  async function send(text:string){
    if(!selectedId) return;
    setError("");
    try{
      await sendMessage.mutateAsync({id:selectedId,text});
      
    }catch (unknownError){
      setError(unknownError instanceof ApiError ? unknownError.message: "发送失败");
      throw unknownError;
    }
  }

  return (
    <main className="chat-layout">
      <ConversationList
        conversations={conversations.data ?? []}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onCreate={()=>createConversation.mutate()}
        creating={createConversation.isPending}
        />
      <section>
        <h1>BioScholar Copilot</h1>
        {error && <p role="alert">{error}</p>}
        {selectedId ? (
          <>
            <MessageList messages={messages.data ?? []}/>
            <Composer disabled = {sendMessage.isPending} onSend={send}/>
            </>
        ):(
          <p>请创建或选择一个会话。</p>
        )
      }
      </section>
    </main>
  )
}