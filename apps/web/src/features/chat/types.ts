
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


export type StreamEvent=
| {type: "run_started";run_id:string}
| { type: "text_delta"; run_id: string; text: string }
| { type: "tool_started"; run_id: string; tool: string }
| { type: "tool_completed"; run_id: string; tool: string }
| { type: "run_completed"; run_id: string; latency_ms: number }
| { type: "run_cancelled"; run_id: string; message: string; latency_ms: number }
| { type: "run_error"; run_id: string; code: string; message: string };

export type StreamPhase="idle" | "streaming" | "stopping";