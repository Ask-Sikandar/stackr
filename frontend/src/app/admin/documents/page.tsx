"use client";

import { useCallback, useEffect, useState } from "react";
import type { Document } from "@/types";
import { DocumentTable } from "@/components/admin/DocumentTable";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function DocumentsAdminPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/documents/`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDocuments(data.results ?? data);
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
    const res = await fetch(`${API_URL}/api/documents/${id}/ingest/`, { method: "POST" });
    if (!res.ok) throw new Error(`Ingest failed: HTTP ${res.status}`);
    await fetchDocuments();
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

      {loading && <p className="text-gray-500">Loading documents...</p>}
      {error && <p className="text-red-600">Error: {error}</p>}
      {!loading && !error && (
        <DocumentTable documents={documents} onIngest={handleIngest} />
      )}
    </div>
  );
}
