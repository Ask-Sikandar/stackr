"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { WsInboundMessage } from "@/types";

interface UseWebSocketOptions {
  url: string;
  onMessage: (msg: WsInboundMessage) => void;
  onError?: (err: Event) => void;
  reconnectDelayMs?: number;
}

interface UseWebSocketReturn {
  send: (data: object) => void;
  isConnected: boolean;
  isConnecting: boolean;
}

export function useWebSocket({
  url,
  onMessage,
  onError,
  reconnectDelayMs = 3000,
}: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  // Keep callbacks fresh without re-triggering the connection effect
  onMessageRef.current = onMessage;
  onErrorRef.current = onError;

  const connect = useCallback(() => {
    if (unmountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setIsConnecting(true);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setIsConnecting(false);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WsInboundMessage;
        onMessageRef.current(data);
      } catch {
        // Malformed message — ignore
      }
    };

    ws.onerror = (event) => {
      onErrorRef.current?.(event);
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsConnecting(false);
      if (!unmountedRef.current) {
        // Auto-reconnect
        reconnectTimerRef.current = setTimeout(connect, reconnectDelayMs);
      }
    };
  }, [url, reconnectDelayMs]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();

    return () => {
      unmountedRef.current = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close(1000, "component unmounted");
    };
  }, [connect]);

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { send, isConnected, isConnecting };
}
