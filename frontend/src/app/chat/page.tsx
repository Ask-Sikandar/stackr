"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/lib/api";
import { getProjectUxConfig } from "@/lib/projectUxConfig";
import { getAccessToken, getProjectId } from "@/lib/session";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { ChatWidget } from "@/components/chat/ChatWidget";
import type { Document } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

type DocList = Document[] | { results: Document[] };

function normalizeDocs(payload: DocList): Document[] {
  return Array.isArray(payload) ? payload : payload.results ?? [];
}

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
  const { isCheckingAuth, isAuthenticated } = useAuthGuard();
  const [projectId, setProjectId] = useState<number | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [checkingAccess, setCheckingAccess] = useState(true);
  const [accessError, setAccessError] = useState<string | null>(null);

  useEffect(() => {
    if (isCheckingAuth || !isAuthenticated) return;

    const token = getAccessToken();
    const project = getProjectId();

    if (!token) return;

    if (!project) {
      router.replace("/portal");
      return;
    }

    let canceled = false;

    const verifyChatPrerequisites = async () => {
      setCheckingAccess(true);
      setAccessError(null);

      try {
        const docs = await apiFetch<DocList>("/api/documents/");
        if (canceled) return;

        const hasIngestedDoc = normalizeDocs(docs).some(
          (doc) => doc.project_id === project && doc.processed,
        );

        if (!hasIngestedDoc) {
          router.replace("/admin/documents?required=ingest");
          return;
        }

        setAccessToken(token);
        setProjectId(project);
      } catch (err) {
        if (canceled) return;
        setAccessError(err instanceof Error ? err.message : "Failed to verify chat prerequisites.");
      } finally {
        if (!canceled) {
          setCheckingAccess(false);
        }
      }
    };

    void verifyChatPrerequisites();

    return () => {
      canceled = true;
    };
  }, [isAuthenticated, isCheckingAuth, router]);

  const leadId = useMemo(() => {
    if (!projectId) return "";
    return getLeadId(projectId);
  }, [projectId]);

  const projectUxConfig = useMemo(() => {
    if (!projectId) return null;
    return getProjectUxConfig(projectId);
  }, [projectId]);

  if (isCheckingAuth || checkingAccess) {
    return <main className="min-h-screen bg-slate-50 p-8 text-slate-500">Preparing workspace...</main>;
  }

  if (accessError) {
    return (
      <main className="min-h-screen bg-slate-50 p-8">
        <div className="mx-auto max-w-2xl rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
          <p className="text-sm font-semibold">Unable to open chat.</p>
          <p className="mt-1 text-sm">{accessError}</p>
          <div className="mt-3 flex gap-3 text-sm">
            <a href="/portal" className="text-blue-700 hover:underline">Go to Portal</a>
            <a href="/admin/documents" className="text-blue-700 hover:underline">Go to Documents</a>
          </div>
        </div>
      </main>
    );
  }

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
            introMessage={projectUxConfig?.introMessage}
            assistantName={projectUxConfig?.assistantDisplayName}
          />
        </div>
      </div>
    </main>
  );
}
