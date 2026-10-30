import {
  ChatContainerContent,
  ChatContainerRoot,
  ChatContainerScrollAnchor,
} from "@/components/ui/chat-container";
import { Loader } from "@/components/ui/loader";
import { Message as MessageView, MessageContent } from "@/components/ui/message";
import { ScrollButton } from "@/components/ui/scroll-button";

type Props = {
  messages: Message[];
  loading: boolean;
  generating: boolean;
};

import type { Message } from "./types";

export function MessageList({ messages, loading, generating }: Props) {
  if (loading) {
    return (
      <div className="grid h-full place-items-center" role="status">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader variant="typing" size="sm" />
          <span>正在加载消息…</span>
        </div>
      </div>
    );
  }

  if (messages.length === 0 && !generating) {
    return (
      <div className="grid h-full place-items-center p-8 text-center text-muted-foreground">
        <div>
          <h2 className="text-lg font-medium text-foreground">开始一个新对话</h2>
          <p>可以先问：PCR 是什么？</p>
        </div>
      </div>
    );
  }

  return (
    <ChatContainerRoot className="relative min-h-0 flex-1">
      <ChatContainerContent className="mx-auto max-w-3xl gap-6 p-4 md:p-6">
        {messages.map((message) => {
          const assistant = message.role === "assistant";
          return (
            <MessageView
              key={message.id}
              className={assistant ? "w-full justify-start" : "w-full justify-end"}
            >
              <div className={assistant ? "max-w-[99%]" : "w-max max-w-[85%] shrink-0"}>
                <MessageContent
                  id={message.id}
                  markdown={assistant}
                  className={
                    assistant
                      ? "min-w-0 max-w-full text-foreground [&_strong]:text-foreground"
                      : "w-full max-w-full whitespace-pre-wrap break-words bg-primary text-primary-foreground"
                  }
                >
                  {message.content}
                </MessageContent>
                {assistant && message.status !== "completed" && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {message.status === "canceled" ? "已停止" : message.status === "failed" ? "生成失败" : "生成中"}
                  </p>
                )}
              </div>
            </MessageView>
          );
        })}

        {generating && messages[messages.length - 1]?.content === "" && (
          <div
            className="flex items-center gap-2 text-sm text-muted-foreground"
            role="status"
          >
            <Loader variant="typing" size="sm" />
            <span>BioScholar 正在回答…</span>
          </div>
        )}
        <ChatContainerScrollAnchor />
      </ChatContainerContent>
      <ScrollButton className="absolute bottom-4 right-4" />
    </ChatContainerRoot>
  );
}
