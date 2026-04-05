"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { Lead } from "@/types";
import { LeadDashboard } from "@/components/admin/LeadDashboard";
import { apiFetch } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { getProjectId } from "@/lib/session";

type LeadList = Lead[] | { results: Lead[] };

function normalizeLeads(payload: LeadList): Lead[] {
  return Array.isArray(payload) ? payload : payload.results ?? [];
}

export default function LeadsAdminPage() {
  const router = useRouter();
  const { isCheckingAuth, isAuthenticated } = useAuthGuard();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isCheckingAuth || !isAuthenticated) return;

    (async () => {
      const selectedProject = getProjectId();
      if (!selectedProject) {
        router.replace("/portal");
        return;
      }

      setProjectId(selectedProject);

      try {
        const data = await apiFetch<LeadList>(`/api/leads/?project_id=${selectedProject}`);
        const leadRows = normalizeLeads(data);

        // Fetch intent events for each lead
        const leadsWithEvents = await Promise.all(
          leadRows.map(async (lead: Lead) => {
            try {
              return await apiFetch<Lead>(`/api/leads/${lead.lead_id}/?project_id=${selectedProject}`);
            } catch {
              return lead;
            }
          })
        );
        setLeads(leadsWithEvents);
      } catch (err) {
        setError(String(err));
      } finally {
        setLoading(false);
      }
    })();
  }, [isAuthenticated, isCheckingAuth, router]);

  if (isCheckingAuth || !isAuthenticated) {
    return <main className="min-h-screen bg-slate-50 p-8 text-slate-500">Checking access...</main>;
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Lead Intelligence</h1>
          <p className="text-sm text-gray-500">
            Prospect activity, intent signals, and lead scores — ordered by score (project {projectId ?? "-"})
          </p>
        </div>
        <a href="/admin/documents" className="text-sm text-blue-600 hover:underline">
          ← Documents
        </a>
      </div>

      {/* Score legend */}
      <div className="mb-4 flex gap-4 text-xs text-gray-500">
        <span><strong className="text-gray-600">1pt</strong> = general</span>
        <span><strong className="text-blue-600">5pt</strong> = availability</span>
        <span><strong className="text-blue-700">10pt</strong> = pricing</span>
        <span><strong className="text-orange-600">25pt</strong> = conversion</span>
      </div>

      {loading && <p className="text-gray-500">Loading leads...</p>}
      {error && <p className="text-red-600">Error: {error}</p>}
      {!loading && !error && <LeadDashboard leads={leads} />}
    </div>
  );
}
