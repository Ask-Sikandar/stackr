"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Document, IngestionJob } from "@/types";
import { DocumentTable } from "@/components/admin/DocumentTable";
import { apiFetch } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { getProjectUxConfig, saveProjectUxConfig } from "@/lib/projectUxConfig";
import { getProjectId } from "@/lib/session";

type DocList = Document[] | { results: Document[] };
type IngestionStatus = IngestionJob["status"];

interface WelcomeMessageGenerateResponse {
  message: string;
  max_length: number;
  source_document_count: number;
  used_processed_documents: boolean;
  generated_with_fallback: boolean;
}

const IN_PROGRESS_STATUSES: IngestionStatus[] = ["queued", "running"];
const IN_PROGRESS_POLL_INTERVAL_MS = 1500;
const WELCOME_MESSAGE_MAX_LENGTH = 280;

function normalizeDocs(payload: DocList): Document[] {
  return Array.isArray(payload) ? payload : payload.results ?? [];
}

function isInProgressStatus(status: IngestionStatus): boolean {
  return IN_PROGRESS_STATUSES.includes(status);
}

export default function DocumentsAdminPage() {
  const { isCheckingAuth, isAuthenticated } = useAuthGuard();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadContent, setUploadContent] = useState("");
  const [uploading, setUploading] = useState(false);
  const [ingestingByDocumentId, setIngestingByDocumentId] = useState<Record<number, boolean>>({});
  const [ingestionJobsByDocumentId, setIngestionJobsByDocumentId] = useState<Record<number, IngestionJob>>({});
  const [welcomeMessage, setWelcomeMessage] = useState("");
  const [welcomeStatus, setWelcomeStatus] = useState<string | null>(null);
  const [welcomeError, setWelcomeError] = useState<string | null>(null);
  const [generatingWelcome, setGeneratingWelcome] = useState(false);

  const mountedRef = useRef(true);
  const pollTimersRef = useRef<Record<number, ReturnType<typeof setTimeout>>>({});

  const clearPollTimer = useCallback((documentId: number) => {
    const existingTimer = pollTimersRef.current[documentId];
    if (existingTimer) {
      clearTimeout(existingTimer);
      delete pollTimersRef.current[documentId];
    }
  }, []);

  const trackIngestionJob = useCallback((job: IngestionJob) => {
    setIngestionJobsByDocumentId((prev) => ({
      ...prev,
      [job.document_id]: job,
    }));
  }, []);

  const fetchDocuments = useCallback(async () => {
    const selectedProject = getProjectId();
    if (!selectedProject) {
      setError("Select a project from /portal first.");
      setDocuments([]);
      setLoading(false);
      return;
    }

    setProjectId(selectedProject);

    try {
      const data = await apiFetch<DocList>("/api/documents/");
      const filtered = normalizeDocs(data).filter((d) => d.project_id === selectedProject);
      setDocuments(filtered);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  const pollIngestionJob = useCallback(
    async (documentId: number, jobId: string) => {
      if (!mountedRef.current) return;

      try {
        const job = await apiFetch<IngestionJob>(`/api/documents/ingest-jobs/${jobId}/`);
        if (!mountedRef.current) return;

        trackIngestionJob(job);

        if (isInProgressStatus(job.status)) {
          clearPollTimer(documentId);
          pollTimersRef.current[documentId] = setTimeout(() => {
            void pollIngestionJob(documentId, jobId);
          }, IN_PROGRESS_POLL_INTERVAL_MS);
          return;
        }

        clearPollTimer(documentId);

        if (job.status === "succeeded") {
          setIngestionJobsByDocumentId((prev) => {
            const next = { ...prev };
            delete next[documentId];
            return next;
          });
          await fetchDocuments();
        }
      } catch (err) {
        if (mountedRef.current) {
          setError(`Failed to refresh ingestion status: ${String(err)}`);
        }
      }
    },
    [clearPollTimer, fetchDocuments, trackIngestionJob],
  );

  useEffect(() => {
    if (isCheckingAuth || !isAuthenticated) return;

    mountedRef.current = true;
    fetchDocuments();

    return () => {
      mountedRef.current = false;
      Object.keys(pollTimersRef.current).forEach((key) => {
        const documentId = Number(key);
        clearPollTimer(documentId);
      });
    };
  }, [clearPollTimer, fetchDocuments, isAuthenticated, isCheckingAuth]);

  useEffect(() => {
    if (!projectId) return;
    const existingConfig = getProjectUxConfig(projectId);
    setWelcomeMessage(existingConfig?.introMessage ?? "");
    setWelcomeStatus(null);
    setWelcomeError(null);
  }, [projectId]);

  const handleIngest = async (id: number) => {
    setError(null);
    setIngestingByDocumentId((prev) => ({ ...prev, [id]: true }));
    clearPollTimer(id);

    try {
      const job = await apiFetch<IngestionJob>(`/api/documents/${id}/ingest/`, { method: "POST" });
      if (!mountedRef.current) return;

      trackIngestionJob(job);

      if (isInProgressStatus(job.status)) {
        void pollIngestionJob(id, job.job_id);
      } else if (job.status === "succeeded") {
        await fetchDocuments();
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(String(err));
      }
    } finally {
      if (mountedRef.current) {
        setIngestingByDocumentId((prev) => ({ ...prev, [id]: false }));
      }
    }
  };

  const handleUpload = async () => {
    if (!projectId || !uploadTitle.trim() || !uploadContent.trim()) return;
    setUploading(true);
    setError(null);
    try {
      await apiFetch("/api/documents/", {
        method: "POST",
        body: JSON.stringify({
          title: uploadTitle.trim(),
          content: uploadContent.trim(),
          source_type: "markdown",
          project_id: projectId,
        }),
      });
      setUploadTitle("");
      setUploadContent("");
      await fetchDocuments();
    } catch (err) {
      setError(String(err));
    } finally {
      setUploading(false);
    }
  };

  const activeIngestionCount = useMemo(
    () =>
      Object.values(ingestionJobsByDocumentId).filter((job) => isInProgressStatus(job.status)).length,
    [ingestionJobsByDocumentId],
  );

  const handleAutoGenerateWelcome = async () => {
    if (!projectId) {
      setWelcomeError("Select a project in portal first.");
      setWelcomeStatus(null);
      return;
    }

    if (documents.length === 0) {
      setWelcomeError("Upload at least one document before generating a welcome message.");
      setWelcomeStatus(null);
      return;
    }

    setGeneratingWelcome(true);
    setWelcomeError(null);
    setWelcomeStatus(null);

    try {
      const response = await apiFetch<WelcomeMessageGenerateResponse>(
        "/api/documents/welcome-message/generate/",
        {
          method: "POST",
          body: JSON.stringify({
            project_id: projectId,
            max_length: WELCOME_MESSAGE_MAX_LENGTH,
          }),
        },
      );

      setWelcomeMessage(response.message);

      const sourceTypeLabel = response.used_processed_documents ? "processed" : "uploaded";
      if (response.generated_with_fallback) {
        setWelcomeStatus("Generated using fallback copy. You can edit and save it.");
      } else {
        setWelcomeStatus(
          `Generated from ${response.source_document_count} ${sourceTypeLabel} document${response.source_document_count > 1 ? "s" : ""}. Review and save.`,
        );
      }
    } catch (err) {
      setWelcomeError(err instanceof Error ? err.message : "Failed to generate welcome message.");
    } finally {
      setGeneratingWelcome(false);
    }
  };

  const handleSaveWelcomeMessage = () => {
    if (!projectId) {
      setWelcomeError("Select a project in portal first.");
      setWelcomeStatus(null);
      return;
    }

    const trimmed = welcomeMessage.trim();
    if (!trimmed) {
      setWelcomeError("Welcome message cannot be empty.");
      setWelcomeStatus(null);
      return;
    }

    if (trimmed.length > WELCOME_MESSAGE_MAX_LENGTH) {
      setWelcomeError(`Welcome message must be ${WELCOME_MESSAGE_MAX_LENGTH} characters or fewer.`);
      setWelcomeStatus(null);
      return;
    }

    const existingConfig = getProjectUxConfig(projectId);
    saveProjectUxConfig(projectId, {
      introMessage: trimmed,
      assistantDisplayName: existingConfig?.assistantDisplayName,
    });

    setWelcomeError(null);
    setWelcomeStatus("Saved. This message will be used as the first chat message for this project.");
  };

  if (isCheckingAuth || !isAuthenticated) {
    return <main className="min-h-screen bg-slate-50 p-8 text-slate-500">Checking access...</main>;
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <p className="text-sm text-gray-500">Manage and ingest product documentation</p>
        </div>
        <a href="/admin/leads" className="text-sm text-blue-600 hover:underline">
          Lead Dashboard →
        </a>
      </div>

      <div className="mb-6 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-900">Upload Document</h2>
        <p className="mt-1 text-xs text-gray-500">Current project: {projectId ?? "not selected"}</p>
        <div className="mt-3 space-y-2">
          <input
            value={uploadTitle}
            onChange={(e) => setUploadTitle(e.target.value)}
            placeholder="Document title"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <textarea
            value={uploadContent}
            onChange={(e) => setUploadContent(e.target.value)}
            placeholder="Paste markdown content"
            className="h-28 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <button
            onClick={handleUpload}
            disabled={uploading || !projectId}
            className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
      </div>

      <div className="mb-6 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-900">Chat Welcome Message</h2>
        <p className="mt-1 text-xs text-gray-500">
          Keep project creation minimal. Configure or auto-generate the welcome message here from project docs.
        </p>
        <div className="mt-3 space-y-2">
          <textarea
            value={welcomeMessage}
            onChange={(e) => setWelcomeMessage(e.target.value)}
            placeholder="Generate a welcome message from documents or write one manually"
            maxLength={WELCOME_MESSAGE_MAX_LENGTH}
            className="h-24 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <p className="text-xs text-gray-500">{welcomeMessage.trim().length}/{WELCOME_MESSAGE_MAX_LENGTH} characters</p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleAutoGenerateWelcome}
              disabled={!projectId || documents.length === 0 || generatingWelcome}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {generatingWelcome ? "Generating..." : "Auto-generate from documents"}
            </button>
            <button
              onClick={handleSaveWelcomeMessage}
              disabled={!projectId || generatingWelcome}
              className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              Save welcome message
            </button>
          </div>
          {welcomeStatus && <p className="text-xs text-emerald-700">{welcomeStatus}</p>}
          {welcomeError && <p className="text-xs text-red-600">{welcomeError}</p>}
        </div>
      </div>

      {activeIngestionCount > 0 && (
        <div className="mb-4 rounded-xl border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
          {activeIngestionCount} document{activeIngestionCount > 1 ? "s" : ""} currently ingesting. You can stay on this page while we keep updating progress.
        </div>
      )}

      {loading && <p className="text-gray-500">Loading documents...</p>}
      {error && <p className="text-red-600">Error: {error}</p>}
      {!loading && !error && (
        <DocumentTable
          documents={documents}
          onIngest={handleIngest}
          ingestingByDocumentId={ingestingByDocumentId}
          ingestionJobsByDocumentId={ingestionJobsByDocumentId}
        />
      )}
    </div>
  );
}
