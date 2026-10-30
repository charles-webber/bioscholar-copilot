import { useState } from "react";
import { useMutation,useQuery,useQueryClient } from "@tanstack/react-query";
import { ApiError, apiFetch } from "../../lib/api/client";
import {ThemeToggle} from "@/components/ThemeToggle";
import { chatApi,chatKeys } from "./api";
import { Composer } from "./Composer";
import { ConversationList } from "./ConversationList";
import { MessageList } from "./MessageList";
import { Variable } from "lucide-react";
import { useChatStream } from "./useChatStream";

function readableError(error:unknown,fallback:string):string{
  if (error instanceof ApiError){
    return error.nextAction
      ? `${error.message} ${error.nextAction}`
      :error.message
  }
  return error instanceof Error ? error.message:fallback;
}



export function ChatPage(){
  const queryClient = useQueryClient();
  const [selectedId,setSelectedId] = useState<string|null>(null);
  const [actionError,setActionError]=useState<string|null>(null);
  const stream = useChatStream();


  const conversations = useQuery({
    queryKey:chatKeys.conversations(),
    queryFn:chatApi.listConversations,
  });
  const messages = useQuery({
    queryKey:
      selectedId===null
        ? [...chatKeys.all,"message","idle"]
        :chatKeys.messages(selectedId),
    queryFn:()=>{
      if(selectedId===null) throw new Error("尚未选择会话");
      return chatApi.listMessages(selectedId);
    },
    enabled:selectedId !== null,
  });

  const createMutation = useMutation({
    mutationFn:()=>chatApi.createConversation(),
    onSuccess:async(created)=>{
      setSelectedId(created.id);
      await queryClient.invalidateQueries({
        queryKey:chatKeys.conversations(),
      })
    }
  })


  
  // const sendMutation=useMutation({
  //   mutationFn:({id,text}:{id:string,text:string})=>chatApi.sendMessage(id,text),
  //   onSettled:async (_data,_error,variables)=>{
  //     await Promise.all([
  //       queryClient.invalidateQueries({
  //         queryKey:chatKeys.messages(variables.id),
  //       }),  
  //       queryClient.invalidateQueries({
  //         queryKey:chatKeys.conversations(),
  //       }),
  //     ]);
  //   },
  // });

  const deleteMutation = useMutation({
    mutationFn:chatApi.deleteConversation,
    onSuccess:async (_data,deleteId)=>{
      queryClient.removeQueries({
        queryKey:chatKeys.messages(deleteId),
        exact:true,
      });
      setSelectedId((current)=>(current === deleteId?null:current));
      await queryClient.invalidateQueries({
        queryKey:chatKeys.conversations(),
      });
    },
  });


async function createConversation(){
    if (createMutation.isPending) return;
    setActionError(null);
    try{
      await createMutation.mutateAsync();
    }catch(error){
      setActionError(readableError(error,"创建会话失败"));
    }
  }


  async function sendMessage(text: string) {
    if (selectedId === null || stream.isStreaming) return;
    setActionError(null);
    stream.clearError();
    await stream.send(selectedId,text);
    }

  async function deleteConversation(id: string) {
    if (deleteMutation.isPending||id===stream.activeConversationId) return;
    setActionError(null);
    try {
      await deleteMutation.mutateAsync(id);
    } catch (error) {
      setActionError(readableError(error, "删除会话失败"));
      throw error;
    }
  }

  const selectedConversation = conversations.data?.find(
    (item) => item.id === selectedId,
  );
  const queryError = conversations.isError
    ? readableError(conversations.error, "加载会话失败")
    : messages.isError
      ? readableError(messages.error, "加载消息失败")
      : null;
  const visibleError = actionError ?? queryError;
  const generatingSelected = stream.activeConversationId===selectedId;  
  return (
    <main className="grid h-svh grid-cols-1 overflow-hidden bg-background text-foreground md:grid-cols-[280px_minmax(0,1fr)]">
      <ConversationList
        conversations={conversations.data ?? []}
        selectedId={selectedId}
        onSelect={(id)=>{
          if (stream.isStreaming) return;
          setActionError(null);
          setSelectedId(id);
        }}
        onCreate={()=>createConversation()}
        onDelete={deleteConversation}
        loading={conversations.isPending}
        creating={createMutation.isPending}
        deletingId={
          deleteMutation.isPending ? deleteMutation.variables:null
        }
        deleteBlockedId={
          stream.activeConversationId
        }
      />
      <section className="grid min-h-0 grid-rows-[auto_auto_minmax(0,1fr)_auto]">
        <header className="flex items-center justify-between border-b px-4 py-3">
          <div className="min-w-0">
            <h1 className="truncate font-semibold">
              {selectedConversation?.title??"BioScholar Copilot"}
            </h1>
            <p className="text-xs text-muted-foreground">
              仅用于生物医学学习
            </p>
          </div>
          <ThemeToggle />
        </header>

        <div aria-live="polite">
          {visibleError && (
            <div
              className="border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive"
              role="alert"
            >
              {visibleError}
            </div>
          )}
        </div>

        {selectedId===null ?(
          <div className="grid min-h-0 place-items-center p-8 text-center text-muted-foreground">
            <div>
              <h2 className="text-lg font-medium text-foreground">
              选择或创建一个会话
              </h2>
              <p>历史会话在左侧，新问题会保存在数据库中。</p>
            </div>
          </div>
        ):(
          <MessageList
            messages={messages.data??[]}
            loading={messages.isPending}
            generating={generatingSelected}
          />
        )}
        {selectedId !== null && (
          <Composer
            disabled={stream.isStreaming}
            generating={generatingSelected}
            stopping={stream.phase==="stopping"}
            onSend={sendMessage}
            onStop={stream.stop}
          />
        )}  
      </section>  
    </main>  
  );
}