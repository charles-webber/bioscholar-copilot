
import { useState, type FormEvent } from "react";

import { apiFetch, ApiError } from "../../lib/api/client";
import type { ChatResponse } from "./types";

export function ChatPage() {
  // 输入内容
  const [message, setMessage] = useState("");

  // 模型回答
  const [result, setResult] = useState<ChatResponse | null>(null);

  // 错误信息
  const [error, setError] = useState("");

  // 请求状态
  const [loading, setLoading] = useState(false);

  // 处理消息提交
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const text = message.trim();

    // 防止空消息和重复提交
    if (!text || loading) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      // 向 FastAPI 发送 POST 请求
      const data = await apiFetch<ChatResponse>("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          message: text,
        }),
      });

      // 更新模型回答
      setResult(data);
    } catch (error) {
      // 处理结构化 API 错误
      if (error instanceof ApiError) {
        setError(
          `${error.message}${
            error.nextAction ? `；${error.nextAction}` : ""
          }`,
        );
      } else {
        setError("网络异常，请稍后重试。");
      }
    } finally {
      // 请求结束，关闭 Loading
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <h1>BioScholar Copilot</h1>

      {/* 安全提示 */}
      <p>
        本工具仅用于生物医学学习，
        不提供临床诊断、处方或剂量建议。
      </p>

      {/* 输入表单 */}
      <form onSubmit={submit}>
        <label htmlFor="question">
          请输入你的生物医学问题
        </label>

        <textarea
          id="question"
          value={message}
          maxLength={4000}
          placeholder="例如：PCR 的基本原理是什么？"
          onChange={(event) => setMessage(event.target.value)}
          rows={5}
        />

        {/* 发送按钮 */}
        <button
          type="submit"
          disabled={loading || !message.trim()}
        >
          {loading ? "回答中..." : "发送"}
        </button>
      </form>

      {/* Loading 提示 */}
      {loading && (
        <p role="status">
          正在生成回答，请稍候...
        </p>
      )}

      {/* 错误提示 */}
      {error && (
        <p role="alert">
          {error}
        </p>
      )}

      {/* 显示模型回答 */}
      {result && (
        <article>
          <h2>回答</h2>

          <p style={{ whiteSpace: "pre-wrap" }}>
            {result.answer}
          </p>

          {/* 显示引用来源 */}
          {result.citations?.length > 0 && (
            <section>
              <h3>参考来源</h3>

              <ul>
                {result.citations.map((citation, index) => (
                  <li key={`${citation.document_id}-${index}`}>
                    <strong>{citation.title}</strong>

                    {citation.page != null && (
                      <span> · 第 {citation.page} 页</span>
                    )}

                    <p>{citation.quote}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </article>
      )}
    </main>
  );
}
