import type { Conversation } from "./api";

type Props = {
    conversations: Conversation[];
    selectedId: string | null;
    onSelect: (id: string) => void;
    onCreate: () => void;
    creating: boolean;
};

export function ConversationList(props:Props){
    return(
        <aside>
            <button onClick={props.onCreate} disabled = {props.creating}>
                {props.creating ? "创建中…" : "新对话" }
                </button>
                <nav aria-label="会话列表">
                    {props.conversations.map((item)=>(
                        <button
                            key={item.id}
                            aria-current={item.id===props.selectedId ? "page":undefined}
                            onClick={()=>props.onSelect(item.id)}
                        >
                            {item.title}
                        </button>    
                    ))}
                    </nav>
                </aside>
    );
}