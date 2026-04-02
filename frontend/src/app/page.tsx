/**
 * Demo page — embeds the ChatWidget for prospect testing.
 * In production this would be a script-tag embeddable widget.
 */
"use client";

import { useMemo } from "react";
import { ChatWidget } from "@/components/chat/ChatWidget";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

function generateLeadId(): string {
  // Persist lead ID in sessionStorage for the duration of the browser session
  const key = "memox_lead_id";
  if (typeof window !== "undefined") {
    const existing = sessionStorage.getItem(key);
    if (existing) return existing;
    const id = crypto.randomUUID();
    sessionStorage.setItem(key, id);
    return id;
  }
  return crypto.randomUUID();
}

export default function HomePage() {
  const leadId = useMemo(() => generateLeadId(), []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4">
      {/* Hero */}
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-extrabold text-gray-900">Pacific Container Co.</h1>
        <p className="mt-2 text-gray-500">
          Ask ContainerBot about sizes, pricing, delivery, or place an order.
        </p>
      </div>

      {/* Chat widget */}
      <div className="w-full max-w-xl" style={{ height: "600px" }}>
        <ChatWidget leadId={leadId} apiUrl={API_URL} wsUrl={WS_URL} />
      </div>

      {/* Admin link */}
      <p className="mt-6 text-xs text-gray-400">
        <a href="/admin/documents" className="underline hover:text-gray-600">
          Admin panel
        </a>
      </p>
    </main>
  );
}
