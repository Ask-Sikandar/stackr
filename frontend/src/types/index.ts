// ---------------------------------------------------------------------------
// Chat / Message types
// ---------------------------------------------------------------------------

export type Intent = "pricing" | "availability" | "general" | "conversion";
export type MessageRole = "user" | "assistant";

export interface Source {
  title: string;
  excerpt: string;
  score: number;
  chunk_index: number;
}

export interface ProductComparisonData {
  products: Array<{
    name: string;
    price: string;
    size: string;
    capacity?: string;
  }>;
}

export interface CTAData {
  label: string;
  description: string;
  action: string;
  variant: "primary" | "secondary";
}

export type Component =
  | { type: "product_comparison"; data: ProductComparisonData }
  | { type: "cta"; label: string; description: string; action: string; variant: string };

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  intent?: Intent;
  sources?: Source[];
  components?: Component[];
  handoff_triggered?: boolean;
  lead_score?: number;
  // Streaming state — not from API, managed by hook
  isStreaming?: boolean;
  streamBuffer?: string;
}

// ---------------------------------------------------------------------------
// WebSocket message types
// ---------------------------------------------------------------------------

export type WsInboundMessage =
  | { type: "typing"; status: boolean }
  | { type: "stream"; token: string }
  | { type: "message"; message_id: string; content: string; intent: Intent; sources: Source[]; components: Component[]; handoff_triggered: boolean; lead_score: number }
  | { type: "error"; message: string };

// ---------------------------------------------------------------------------
// Document / Admin types
// ---------------------------------------------------------------------------

export interface Document {
  id: number;
  title: string;
  source_type: string;
  uploaded_at: string;
  processed: boolean;
  chunk_count: number;
}

export interface Chunk {
  id: number;
  chunk_index: number;
  content: string;
  metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Lead / Dashboard types
// ---------------------------------------------------------------------------

export interface IntentEvent {
  intent: Intent;
  message_preview: string;
  score_delta: number;
  created_at: string;
}

export interface Lead {
  id: number;
  lead_id: string;
  score: number;
  last_intent: string;
  last_seen_at: string;
  message_count: number;
  intent_events?: IntentEvent[];
}
