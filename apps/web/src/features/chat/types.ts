
export type Citation = {
  document_id: string;
  title: string;
  page?: number | null;
  quote: string;
};

export type ChatResponse = {
  conversation_id: string;
  answer: string;
  citations: Citation[];
  finish_reason?: "stop" | "length" | "error";
};

export type Conversation = {
  id:string;
  title:string;
  created_at:string;
  updated_at:string;
};

export type Message = {
  id:string;
  role:"user"|"assistant";
  content:string;
  status:string;
  created_at:string;
}