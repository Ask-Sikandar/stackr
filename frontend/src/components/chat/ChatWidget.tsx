"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage, WsInboundMessage } from "@/types";
import { useWebSocket } from "@/hooks/useWebSocket";
import { MessageBubble } from "./MessageBubble";

interface ChatWidgetProps {
  leadId: string;
  apiUrl: string;
  wsUrl: string;
}

function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="rounded-2xl rounded-bl-sm bg-white border border-gray-200 px-4 py-3 shadow-sm">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="h-2 w-2 rounded-full bg-gray-400 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function ConnectionBanner({ isConnecting }: { isConnecting: boolean }) {
  if (!isConnecting) return null;
  return (
    <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-2 text-xs text-yellow-700 text-center">
      Connecting to assistant...
    </div>
  );
}

export function ChatWidget({ leadId, apiUrl: _apiUrl, wsUrl }: ChatWidgetProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hi! I'm ContainerBot. I can help you find the right shipping container, get pricing, check delivery to your location, and answer any questions. What can I help you with?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleWsMessage = useCallback((msg: WsInboundMessage) => {
    setError(null);

    if (msg.type === "typing") {
      setIsTyping(msg.status);
      if (msg.status) {
        // Add a placeholder streaming bubble
        setMessages((prev) => {
          const alreadyStreaming = prev.some((m) => m.isStreaming);
          if (alreadyStreaming) return prev;
          return [
            ...prev,
            {
              id: `streaming-${Date.now()}`,
              role: "assistant",
              content: "",
              isStreaming: true,
              streamBuffer: "",
            },
          ];
        });
      }
    }

    if (msg.type === "stream") {
      setMessages((prev) =>
        prev.map((m) =>
          m.isStreaming
            ? { ...m, streamBuffer: (m.streamBuffer ?? "") + msg.token }
            : m
        )
      );
    }

    if (msg.type === "message") {
      setIsTyping(false);
      // Replace the streaming placeholder with the final structured message
      setMessages((prev) => {
        const withoutStreaming = prev.filter((m) => !m.isStreaming);
        return [
          ...withoutStreaming,
          {
            id: msg.message_id,
            role: "assistant",
            content: msg.content,
            intent: msg.intent,
            sources: msg.sources,
            components: msg.components,
            handoff_triggered: msg.handoff_triggered,
            lead_score: msg.lead_score,
          },
        ];
      });
    }

    if (msg.type === "error") {
      setIsTyping(false);
      setMessages((prev) => prev.filter((m) => !m.isStreaming));
      setError(msg.message);
    }
  }, []);

  const { send, isConnected, isConnecting } = useWebSocket({
    url: `${wsUrl}/ws/chat/${leadId}/`,
    onMessage: handleWsMessage,
    onError: () => setError("Connection error — retrying..."),
  });

  // Clear the error banner as soon as the connection is established.
  // Needed because React Strict Mode double-invokes effects, causing the
  // first WS to close with an error before the second one connects cleanly.
  useEffect(() => {
    if (isConnected) setError(null);
  }, [isConnected]);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text || !isConnected) return;

    setMessages((prev) => [
      ...prev,
      { id: `user-${Date.now()}`, role: "user", content: text },
    ]);
    setInput("");
    send({ type: "chat", message: text, lead_id: leadId });
  }, [input, isConnected, send, leadId]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full flex-col rounded-2xl border border-gray-200 bg-gray-50 shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-blue-600 px-4 py-3 flex items-center gap-3">
        <div className="h-8 w-8 rounded-full bg-white/20 flex items-center justify-center text-white text-sm font-bold">
          CB
        </div>
        <div>
          <p className="text-sm font-semibold text-white">ContainerBot</p>
          <p className="text-xs text-blue-200">Pacific Container Co. Sales Assistant</p>
        </div>
        <div className={`ml-auto h-2 w-2 rounded-full ${isConnected ? "bg-green-400" : "bg-yellow-400"}`} />
      </div>

      <ConnectionBanner isConnecting={isConnecting} />

      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isTyping && !messages.some((m) => m.isStreaming) && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border-t border-red-200 px-4 py-2 text-xs text-red-600">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="border-t border-gray-200 bg-white p-3 flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isConnected ? "Ask about containers, pricing, delivery..." : "Connecting..."}
          disabled={!isConnected}
          className="flex-1 rounded-xl border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          onClick={handleSend}
          disabled={!isConnected || !input.trim()}
          className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
