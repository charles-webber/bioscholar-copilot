export type Message = {
    id:string;
    role:"user"|"assistant";
    content:string;
};

type ChatState = {
    messages:Message[];
    statusLabel:string|null;
    isStreaming:boolean;
    error:string|null;
};

