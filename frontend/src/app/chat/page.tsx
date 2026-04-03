"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { getAccessToken, getProjectId } from "@/lib/session";
import { ChatWidget } from "@/components/chat/ChatWidget";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

function getLeadId(projectId: number): string {
  const key = `memox_lead_id_${projectId}`;
  const existing = sessionStorage.getItem(key);
  if (existing) return existing;
  const id = crypto.randomUUID();
  sessionStorage.setItem(key, id);
  return id;
}

export default function ChatPage() {
  const router = useRouter();
  const [projectId, setProjectId] = useState<number | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    const project = getProjectId();

    if (!token) {
      router.replace("/login");
      return;
    }

    if (!project) {
      router.replace("/portal");
      return;
    }

    setAccessToken(token);
    setProjectId(project);
  }, [router]);

  const leadId = useMemo(() => {
    if (!projectId) return "";
    return getLeadId(projectId);
  }, [projectId]);

  if (!projectId || !accessToken) {
    return <main className="min-h-screen bg-slate-50 p-8 text-slate-500">Preparing workspace...</main>;
  }

  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-8">
      <div className="mx-auto max-w-3xl">
        <header className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Project Chat</h1>
            <p className="text-sm text-slate-500">Project #{projectId} tenant-scoped assistant</p>
          </div>
          <a href="/portal" className="text-sm text-blue-600 hover:underline">Back to portal</a>
        </header>

        <div className="h-[680px]">
          <ChatWidget
            leadId={leadId}
            apiUrl={API_URL}
            wsUrl={WS_URL}
            projectId={projectId}
            accessToken={accessToken}
          />
        </div>
      </div>
    </main>
  );
}
