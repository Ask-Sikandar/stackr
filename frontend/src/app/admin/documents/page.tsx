"use client";

import { useCallback, useEffect, useState } from "react";
import type { Document } from "@/types";
import { DocumentTable } from "@/components/admin/DocumentTable";
import { apiFetch } from "@/lib/api";
import { getAccessToken, getProjectId } from "@/lib/session";

type DocList = Document[] | { results: Document[] };

function normalizeDocs(payload: DocList): Document[] {
  return Array.isArray(payload) ? payload : payload.results ?? [];
}

export default function DocumentsAdminPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadContent, setUploadContent] = useState("");
  const [uploading, setUploading] = useState(false);

  const fetchDocuments = useCallback(async () => {
    const selectedProject = getProjectId();
    const token = getAccessToken();
    if (!selectedProject || !token) {
      setError("Select a project from /portal and log in first.");
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

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleIngest = async (id: number) => {
    await apiFetch(`/api/documents/${id}/ingest/`, { method: "POST" });
    await fetchDocuments();
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

      {loading && <p className="text-gray-500">Loading documents...</p>}
      {error && <p className="text-red-600">Error: {error}</p>}
      {!loading && !error && (
        <DocumentTable documents={documents} onIngest={handleIngest} />
      )}
    </div>
  );
}
