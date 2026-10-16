users
  id, email, password_hash, created_at

conversations
  id, user_id, title, created_at, updated_at

messages
  id, conversation_id, role, content, status,
  prompt_tokens, completion_tokens, latency_ms, created_at

runs
  id, conversation_id, trace_id, model, status,
  input_json, output_json, error_code, started_at, finished_at

documents
  id, user_id, title, sha256, mime_type, status, error_message, created_at

document_chunks
  id, document_id, content, page, chunk_index, metadata_json, embedding