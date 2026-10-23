import type { Conversation } from "./types";

import { useState } from "react";
import {Loader2,Plus,Trash2} from "lucide-react"

import{
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,    
}from "@/components/ui/alert-dialog";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Props = {
    conversations: Conversation[];
    selectedId: string | null;
    onSelect: (id: string) => void;
    onCreate: () => void;
    onDelete:(id:string)=>Promise<void>;
    loading:boolean;
    creating: boolean;
    deletingId:string|null;
    deleteBlockedId:string|null;
};

export function ConversationList({
  conversations,
  selectedId,
  onSelect,
  onCreate,
  onDelete,
  loading,
  creating,
  deletingId,
  deleteBlockedId,    
}:Props){
    const [pendingDeleteId,setPendingDeleteId] = useState<string|null>(null);
    const pendingConversation = conversations.find(
        (item)=>item.id === pendingDeleteId,
    );

    async function confirmDelete(){
        if(pendingDeleteId===null||deletingId!==null) return;
        try{
            await onDelete(pendingDeleteId);
            setPendingDeleteId(null);
        }catch{
            // ChatPage 统一显示错误。这里保留弹窗，方便取消或稍后重试。
        }
    }

    return(
        <aside className="flex min-h-0 flex-col border-b bg-card md:border-r md:border-b-0">
            <div className="flex items-center justify-between gap-3 border-b p-3">
                <div>
                    <p className="font-semibold">历史会话</p>
                    <p className="text-xs text-muted-foreground">BioScholar Copilot</p>
                </div>
                <Button
                    type="button"
                    size="sm"
                    onClick={onCreate}
                    disabled={creating}
                >
                    {creating ? (
                        <Loader2 className="animate-spin" aria-hidden="true"/>
                    ):(
                        <Plus aria-hidden="true"/>
                    )}
                    {creating ? "创建中…" : "新对话"}
                </Button>    
            </div>

            <nav
                aria-label="会话列表"
                className="max-h-48 min-h-0 flex-1 space-y-1 overflow-y-auto p-2 md:max-h-none"
            >
                {loading ? (
                    <p className="p-3 text-sm text-muted-foreground" role="status">
                       正在加载会话…
                    </p> 
                ): conversations.length===0?(
                    <p className="p-3 text-sm text-muted-foreground">还没有会话</p>
                ):(
                    conversations.map((item)=>{
                    const selected = item.id===selectedId;
                    const deleting = item.id === deletingId;
                    const blocked = item.id === deleteBlockedId;
                    return (
                        <div
                            key={item.id}
                            className={cn(
                                "group flex items-center gap-1 rounded-lg",
                                selected && "bg-accent",
                            )}
                        >
                            <button
                                type="button"
                                aria-current={selected ? "page" : undefined}
                                className="min-w-0 flex-1 truncate rounded-lg px-3 py-2 text-left text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                onClick={()=>onSelect(item.id)}
                            >
                                {item.title}
                            </button>
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="shrink-0"
                                aria-label={`删除会话：${item.title}`}
                                disabled={deletingId !== null || blocked}
                                onClick={() => setPendingDeleteId(item.id)}
                            >
                                {deleting ? (
                                    <Loader2 className="animate-spin" aria-hidden="true"/>
                                ):(
                                    <Trash2 aria-hidden="true"/>
                                )
                            }
                            </Button>
                        </div>
                    );
                })
            )}
            </nav>

            <AlertDialog
                open={pendingDeleteId!==null}
                onOpenChange={(open)=>{
                    if (!open && deletingId===null) setPendingDeleteId(null);
                }}  
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>删除这个会话？</AlertDialogTitle>
                        <AlertDialogDescription>
                            “{pendingConversation?.title ?? "该会话"}”的消息和运行记录会一起删除，此操作不能撤销。
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={deletingId!==null}>
                            取消
                        </AlertDialogCancel>
                        <AlertDialogAction
                            disabled={deletingId!==null}
                            onClick={(event)=>{
                                event.preventDefault();
                                void confirmDelete();
                            }}
                        >
                            {deletingId !== null ? "删除中…" : "确认删除"}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>    
            </AlertDialog>
        </aside>        
    );
}