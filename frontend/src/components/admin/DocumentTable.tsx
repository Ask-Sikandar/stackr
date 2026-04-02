"use client";

import { useState } from "react";
import type { Document } from "@/types";

interface DocumentTableProps {
  documents: Document[];
  onIngest: (id: number) => Promise<void>;
}

export function DocumentTable({ documents, onIngest }: DocumentTableProps) {
  const [loadingId, setLoadingId] = useState<number | null>(null);

  const handleIngest = async (id: number) => {
    setLoadingId(id);
    try {
      await onIngest(id);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
          <tr>
            <th className="px-4 py-3 text-left">Title</th>
            <th className="px-4 py-3 text-left">Type</th>
            <th className="px-4 py-3 text-left">Uploaded</th>
            <th className="px-4 py-3 text-center">Status</th>
            <th className="px-4 py-3 text-center">Chunks</th>
            <th className="px-4 py-3 text-center">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {documents.map((doc) => (
            <tr key={doc.id} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-medium text-gray-800">{doc.title}</td>
              <td className="px-4 py-3 text-gray-500 capitalize">{doc.source_type}</td>
              <td className="px-4 py-3 text-gray-500">
                {new Date(doc.uploaded_at).toLocaleDateString()}
              </td>
              <td className="px-4 py-3 text-center">
                {doc.processed ? (
                  <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
                    Ingested
                  </span>
                ) : (
                  <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-semibold text-yellow-700">
                    Pending
                  </span>
                )}
              </td>
              <td className="px-4 py-3 text-center text-gray-600">{doc.chunk_count}</td>
              <td className="px-4 py-3 text-center">
                <button
                  onClick={() => handleIngest(doc.id)}
                  disabled={loadingId === doc.id}
                  className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {loadingId === doc.id ? "Processing..." : doc.processed ? "Re-ingest" : "Ingest"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {documents.length === 0 && (
        <div className="py-12 text-center text-gray-400">No documents uploaded yet.</div>
      )}
    </div>
  );
}
