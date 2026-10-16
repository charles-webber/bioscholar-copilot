
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
