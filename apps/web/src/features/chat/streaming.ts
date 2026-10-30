import { ApiError, apiFetch } from "../../lib/api/client";
import type { StreamEvent } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

type ErrorBody = {
  detail?: string | { message?: string; code?: string; next_action?: string };
};

function errorFromBody(status: number, body: ErrorBody | null): ApiError {
  const detail = body?.detail;
  if (typeof detail === "string") return new ApiError(detail, status);
  return new ApiError(
    detail?.message ?? `流式请求失败：${status}`,
    status,
    detail?.code,
    detail?.next_action,
  );
}

function parseFrame(frame: string): StreamEvent | null {
  const data = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");
  if (!data) return null;
  return JSON.parse(data) as StreamEvent;
}

export async function* streamMessage(
  conversationId: string,
  message: string,
  signal: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const response = await fetch(
    `${API_URL}/api/conversations/${conversationId}/messages:stream`,
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
      signal,
    },
  );

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ErrorBody | null;
    throw errorFromBody(response.status, body);
  }
  if (!response.body) throw new Error("浏览器没有返回可读取的响应流");

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const event = parseFrame(frame);
        if (event) yield event;
      }
      if (done) break;
    }
    if (buffer.trim()) {
      const event = parseFrame(buffer);
      if (event) yield event;
    }
  } finally {
    reader.releaseLock();
  }
}

export function cancelRun(runId: string): Promise<{ accepted: boolean; status: string }> {
  return apiFetch<{ accepted: boolean; status: string }>(`/api/runs/${runId}/cancel`, {
    method: "POST",
  });
}