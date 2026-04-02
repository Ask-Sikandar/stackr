"use client";

import type { ChatMessage, Component } from "@/types";
import { SourceCard } from "./SourceCard";
import { ProductComparisonCard } from "./ProductComparisonCard";
import { CTACard } from "./CTACard";

function renderComponent(component: Component, idx: number) {
  if (component.type === "product_comparison") {
    return <ProductComparisonCard key={idx} data={component.data} />;
  }
  if (component.type === "cta") {
    return (
      <CTACard key={idx} label={component.label} description={component.description} />
    );
  }
  return null;
}

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-fade-in`}>
      <div className={`max-w-[85%] space-y-2 ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        {/* Main bubble */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
            isUser
              ? "rounded-br-sm bg-blue-600 text-white"
              : "rounded-bl-sm bg-white text-gray-800 border border-gray-200"
          }`}
        >
          {message.isStreaming ? (
            <>
              {message.streamBuffer}
              <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-blink bg-current align-middle" />
            </>
          ) : (
            <p className="whitespace-pre-wrap">{message.content}</p>
          )}
        </div>

        {/* Rich components — only for assistant messages */}
        {!isUser && !message.isStreaming && (
          <>
            {/* Structured UI components (product comparison, CTA) */}
            {message.components?.map((c, i) => renderComponent(c, i))}

            {/* Source citations */}
            {message.sources && message.sources.length > 0 && (
              <div className="w-full space-y-1">
                <p className="text-xs text-gray-400 font-medium px-1">Sources</p>
                {message.sources.map((src, i) => (
                  <SourceCard key={i} source={src} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
