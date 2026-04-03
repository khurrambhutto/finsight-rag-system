import { useEffect, useRef, useState } from "react";
import { useAuth, useUser } from "@clerk/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import {
  createChatThread,
  fetchChatThread,
  streamChat,
  type ChatMessage,
} from "../../lib/api";
import { useOllamaModel } from "../../lib/ollama-model-context";
import { displayModelId, ModelPicker } from "./model-picker";

const starterPrompts = [
  "Summarize how this milestone is set up.",
  "What is missing before we can add document retrieval?",
  "Explain the current auth flow in one paragraph.",
];

export function ChatPage() {
  const { getToken } = useAuth();
  const { user } = useUser();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { threadId } = useParams();
  const { models, selectedModel, setSelectedModel, isLoading, listsError } =
    useOllamaModel();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamGenRef = useRef(0);
  const skipThreadResetRef = useRef<string | null>(null);

  const threadQuery = useQuery({
    queryKey: ["chatThread", threadId],
    queryFn: () => fetchChatThread(threadId!, () => getToken()),
    enabled: Boolean(threadId),
  });

  useEffect(() => {
    if (threadId && skipThreadResetRef.current === threadId) {
      skipThreadResetRef.current = null;
      return;
    }
    streamGenRef.current += 1;
    setMessages([]);
    setInput("");
    setError(null);
    setIsStreaming(false);
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
    }
  }, [threadId]);

  useEffect(() => {
    if (!threadId || !threadQuery.data || messages.length > 0) {
      return;
    }
    setMessages(threadQuery.data.messages);
  }, [threadId, threadQuery.data, messages.length]);

  const displayName =
    user?.firstName ||
    user?.primaryEmailAddress?.emailAddress?.split("@")[0] ||
    "You";

  function resizeTextarea() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }

  function scrollToBottom() {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  async function handleSubmit(promptText?: string) {
    const nextMessage = (promptText ?? input).trim();

    if (!nextMessage || isStreaming) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: nextMessage,
    };

    const assistantId = crypto.randomUUID();

    setError(null);
    setInput("");
    setIsStreaming(true);

    const gen = streamGenRef.current;

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantId, role: "assistant", content: "" },
    ]);

    setTimeout(scrollToBottom, 50);

    try {
      let activeThreadId = threadId;

      if (!activeThreadId) {
        const createdThread = await createChatThread(() => getToken());
        activeThreadId = createdThread.id;
        skipThreadResetRef.current = activeThreadId;
        void navigate(`/app/chat/${activeThreadId}`, { replace: true });
      }

      if (!activeThreadId) {
        throw new Error("Failed to create chat.");
      }

      await streamChat(
        activeThreadId,
        nextMessage,
        () => getToken(),
        {
          onChunk: (content) => {
            if (streamGenRef.current !== gen) return;
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? { ...message, content: message.content + content }
                  : message,
              ),
            );
            scrollToBottom();
          },
          onError: (message) => {
            if (streamGenRef.current !== gen) return;
            setError(message);
          },
        },
        { model: selectedModel },
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["chatThread", activeThreadId] }),
        queryClient.invalidateQueries({ queryKey: ["chatThreads"] }),
      ]);
    } catch (streamError) {
      if (streamGenRef.current !== gen) return;
      const detail =
        streamError instanceof Error
          ? streamError.message
          : "Streaming failed.";
      setError(detail);
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                content:
                  detail ||
                  "The backend could not complete the response. Check Clerk and Ollama config.",
              }
            : message,
        ),
      );
    } finally {
      if (streamGenRef.current === gen) {
        setIsStreaming(false);
      }
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <div className="chat-page">
      {threadId && threadQuery.isLoading && messages.length === 0 ? (
        <div className="chat-empty-state">
          <p className="composer-hint">Loading chat...</p>
        </div>
      ) : threadQuery.isError ? (
        <div className="chat-empty-state">
          <p className="status-error">
            {threadQuery.error instanceof Error
              ? threadQuery.error.message
              : "Failed to load chat."}
          </p>
        </div>
      ) : null}

      {/* Messages / Welcome */}
      <div className="chat-messages">
        {!threadId && messages.length === 0 ? (
          <div className="welcome-wrap">
            <h2 className="welcome-greeting">Good evening, {displayName}</h2>
            <p className="welcome-sub">
              Local model chat powered by Ollama. Ask anything to get started,
              or pick a prompt below.
            </p>
            <div className="starter-grid">
              {starterPrompts.map((prompt) => (
                <button
                  key={prompt}
                  className="starter-card"
                  onClick={() => void handleSubmit(prompt)}
                  disabled={isStreaming}
                >
                  <span className="starter-hint">Try this</span>
                  <span className="starter-text">{prompt}</span>
                </button>
              ))}
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="chat-empty-state">
            <p className="composer-hint">This chat is saved locally and ready.</p>
          </div>
        ) : (
          <div className="message-list">
            {messages.map((message) => (
              <div key={message.id} className={`message-row ${message.role}`}>
                <span className="message-sender">
                  {message.role === "assistant" ? "Assistant" : displayName}
                </span>
                <div className="message-bubble">
                  {message.content ||
                    (isStreaming && message.role === "assistant" ? (
                      <span className="streaming-cursor" />
                    ) : (
                      ""
                    ))}
                  {isStreaming &&
                    message.role === "assistant" &&
                    message.content && <span className="streaming-cursor" />}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="composer-area">
        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            void handleSubmit();
          }}
        >
          <textarea
            ref={textareaRef}
            value={input}
            rows={1}
            placeholder="Message the assistant… (Enter to send, Shift+Enter for newline)"
            onChange={(e) => {
              setInput(e.target.value);
              resizeTextarea();
            }}
            onKeyDown={handleKeyDown}
          />
          <div className="composer-toolbar">
            <ModelPicker
              models={models}
              selectedModel={selectedModel}
              onSelect={setSelectedModel}
              disabled={isStreaming}
              isLoading={isLoading}
              listError={listsError}
            />
            <button
              type="submit"
              className="send-btn"
              disabled={isStreaming || !input.trim()}
              aria-label="Send message"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path
                  d="M7 11.5V2.5M3 6.5L7 2.5L11 6.5"
                  stroke="currentColor"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
        </form>

        <div className="composer-meta">
          <p className="composer-hint">
            {isStreaming
              ? "Generating response…"
              : listsError
                ? listsError.message
                : selectedModel
                  ? `Using ${displayModelId(selectedModel)}`
                  : "Choose an Ollama model from the picker in the input."}
          </p>
          {error && <p className="status-error">{error}</p>}
        </div>
      </div>
    </div>
  );
}
