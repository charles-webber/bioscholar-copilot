import { useState  ,type SubmitEvent} from "react";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
    PromptInput,
    PromptInputActions,
    PromptInputTextarea,
} from "@/components/ui/prompt-input";


type Props={
    disabled:boolean;
    onSend:(message:string)=>Promise<void>;
};

export function Composer({disabled,onSend}:Props){
    const [message,setMessage] = useState("");

    async function sendCurrent(){
        
            const text = message.trim();
            if(!text||disabled) return;
            try{
                await onSend(text);
                setMessage("");
            }catch{
                // ChatPage 展示错误；保留输入，方便修改或重试。
            }
        }

        return (
            <form
                className="mx-auto w-full max-w-3xl p-4"
                onSubmit={(event)=>{
                    event.preventDefault();
                    void sendCurrent();
                }}
                >
                    <PromptInput
                        value={message}
                        onValueChange={setMessage}
                        onSubmit={()=>void sendCurrent()}
                        isLoading={disabled}
                        disabled={disabled}
                    >
                        <PromptInputTextarea
                            aria-label="问题"
                            maxLength={4000}
                            placeholder="输入问题；Enter 发送，Shift+Enter 换行"
                        />
                        <PromptInputActions className="justify-between px-2 pb-1">
                            <span className="text-xs text-muted-foreground">{message.length}/4000</span>
                            <Button type="submit" size="icon" disabled={disabled || !message.trim()}>
                                <Send aria-hidden="true"/>
                                <span className="sr-only">发送</span>
                            </Button>
                        </PromptInputActions>
                    </PromptInput>
                </form>
        )
}
