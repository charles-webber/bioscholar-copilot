import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { chatKeys } from "./api";
import { cancelRun, streamMessage } from "./streaming";
import type { Message, StreamPhase } from "./types";

type ActiveStream = {
  conversationId: string;
  assistantId: string;
  runId: string | null;
  controller: AbortController;
  terminal: boolean;
};

function now(): string {
  return new Date().toISOString();
}

export function useChatStream() {
  const queryClient = useQueryClient();
  const activeRef = useRef<ActiveStream | null>(null);
  const [phase, setPhase] = useState<StreamPhase>("idle");
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
//更新 AI 聊天气泡
  const patchAssistant = useCallback(
    (active: ActiveStream, update: (message: Message) => Message) => {
      queryClient.setQueryData<Message[]>(
        chatKeys.messages(active.conversationId),
        (old = []) => old.map((item) => (item.id === active.assistantId ? update(item) : item)),
      );
    },
    [queryClient],
  );

  const send = useCallback(
    async (conversationId: string, text: string) => {
      if (activeRef.current) return;
      const userId = `local-user-${crypto.randomUUID()}`;
      const assistantId = `local-assistant-${crypto.randomUUID()}`;
      const controller = new AbortController();
      const active: ActiveStream = {
        conversationId,
        assistantId,
        runId: null,
        controller,
        terminal: false,
      };
      activeRef.current = active;
      setActiveConversationId(conversationId);
      setPhase("streaming");
      setError(null);

      queryClient.setQueryData<Message[]>(chatKeys.messages(conversationId), (old = []) => [
        ...old,
        { id: userId, role: "user", content: text, status: "completed", created_at: now() },
        { id: assistantId, role: "assistant", content: "", status: "streaming", created_at: now() },
      ]);

      try {
        for await (const event of streamMessage(conversationId, text, controller.signal)) {
          if (event.type === "run_started") active.runId = event.run_id;
          if (event.type === "text_delta") {
            patchAssistant(active, (message) => ({
              ...message,
              content: message.content + event.text,
            }));
          }
          if (event.type === "run_completed") {
            active.terminal = true;
            patchAssistant(active, (message) => ({ ...message, status: "completed" }));
          }
          if (event.type === "run_cancelled") {
            active.terminal = true;
            patchAssistant(active, (message) => ({ ...message, status: "cancelled" }));
          }
          if (event.type === "run_error") {
            active.terminal = true;
            patchAssistant(active, (message) => ({ ...message, status: "failed" }));
            throw new Error(event.message);
          }
        }
        if (!active.terminal) throw new Error("流式连接结束，但没有收到运行终态");
      } catch (caught) {
        if (!(caught instanceof DOMException && caught.name === "AbortError")) {
          setError(caught instanceof Error ? caught.message : "流式发送失败");
          throw caught;
        }
      } finally {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: chatKeys.messages(conversationId) }),
          queryClient.invalidateQueries({ queryKey: chatKeys.conversations() }),
        ]);
        if (activeRef.current === active) activeRef.current = null;
        setActiveConversationId(null);
        setPhase("idle");
      }
    },
    [patchAssistant, queryClient],
  );

  const stop = useCallback(async () => {
    const active = activeRef.current;
    if (!active || phase === "stopping") return;
    setPhase("stopping");
    try {
      if (active.runId) await cancelRun(active.runId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "停止运行失败");
    } finally {
      window.setTimeout(() => {
        if (activeRef.current === active && !active.terminal) active.controller.abort();
      }, 1500);
    }
  }, [phase]);

  useEffect(() => {
    return () => {
      const active = activeRef.current;
      if (!active) return;
      if (active.runId) void cancelRun(active.runId).catch(() => undefined);
      active.controller.abort();
    };
  }, []);

  return {
    send,
    stop,
    phase,
    isStreaming: phase !== "idle",
    activeConversationId,
    error,
    clearError: () => setError(null),
  };
}