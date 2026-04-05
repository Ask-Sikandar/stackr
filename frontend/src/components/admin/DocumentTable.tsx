"use client";

import type { Document, IngestionJob } from "@/types";

interface DocumentTableProps {
  documents: Document[];
  onIngest: (id: number) => Promise<void>;
  ingestingByDocumentId: Record<number, boolean>;
  ingestionJobsByDocumentId: Record<number, IngestionJob>;
}

function isJobActive(status: IngestionJob["status"]): boolean {
  return status === "queued" || status === "running";
}

export function DocumentTable({
  documents,
  onIngest,
  ingestingByDocumentId,
  ingestionJobsByDocumentId,
}: DocumentTableProps) {

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
          {documents.map((doc) => {
            const trackedJob = ingestionJobsByDocumentId[doc.id];
            const isSubmitting = Boolean(ingestingByDocumentId[doc.id]);
            const isActivelyIngesting = trackedJob ? isJobActive(trackedJob.status) : false;
            const disableIngestButton = isSubmitting || isActivelyIngesting;

            let buttonLabel = doc.processed ? "Re-ingest" : "Ingest";
            if (isSubmitting) {
              buttonLabel = "Queueing...";
            } else if (isActivelyIngesting) {
              buttonLabel = "Ingesting...";
            } else if (trackedJob?.status === "failed") {
              buttonLabel = "Retry ingest";
            }

            return (
              <tr key={doc.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-800">{doc.title}</td>
                <td className="px-4 py-3 text-gray-500 capitalize">{doc.source_type}</td>
                <td className="px-4 py-3 text-gray-500">
                  {new Date(doc.uploaded_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3 text-center">
                  {trackedJob?.status === "failed" ? (
                    <div className="mx-auto w-28">
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                        Failed
                      </span>
                    </div>
                  ) : isActivelyIngesting ? (
                    <div className="mx-auto w-28 text-left">
                      <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                        {trackedJob.status === "queued" ? "Queued" : "Ingesting"}
                      </span>
                      <div className="mt-1 h-1.5 w-full overflow-hidden rounded bg-blue-100">
                        <div
                          className={`h-full rounded bg-blue-600 animate-pulse ${
                            trackedJob.status === "queued" ? "w-1/3" : "w-2/3"
                          }`}
                        />
                      </div>
                    </div>
                  ) : doc.processed ? (
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
                    onClick={() => onIngest(doc.id)}
                    disabled={disableIngestButton}
                    className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-400 disabled:opacity-100"
                  >
                    {buttonLabel}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {documents.length === 0 && (
        <div className="py-12 text-center text-gray-400">No documents uploaded yet.</div>
      )}
    </div>
  );
}
