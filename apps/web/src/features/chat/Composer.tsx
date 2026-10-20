import { useState  ,type SubmitEvent} from "react";

type Props={
    disabled:boolean;
    onSend:(message:string)=>Promise<void>;
};

export function Composer({disabled,onSend}:Props){
    const [message,setMessage] = useState("");

    async function submit(event:SubmitEvent<HTMLFormElement>){
        event.preventDefault();
        const text = message.trim();
        if(!text||disabled) return;
        await onSend(text);
        setMessage("")
    }


    return(
        <form onSubmit={submit}>
            <label htmlFor="message">问题</label>
            <textarea
                id="message"
                value={message}
                maxLength={4000}
                onChange={(event)=>setMessage(event.target.value)}
            />
            <button disabled={disabled||!message.trim()}>{disabled?"发送中…":"发送"}    
            </button>

        </form>
        
    );
}