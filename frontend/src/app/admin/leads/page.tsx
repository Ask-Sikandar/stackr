"use client";

import { useEffect, useState } from "react";
import type { Lead } from "@/types";
import { LeadDashboard } from "@/components/admin/LeadDashboard";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function LeadsAdminPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/leads/`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        // Fetch intent events for each lead
        const leadsWithEvents = await Promise.all(
          (data.results ?? data).map(async (lead: Lead) => {
            const detailRes = await fetch(`${API_URL}/api/leads/${lead.lead_id}/`);
            if (!detailRes.ok) return lead;
            return detailRes.json();
          })
        );
        setLeads(leadsWithEvents);
      } catch (err) {
        setError(String(err));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Lead Intelligence</h1>
          <p className="text-sm text-gray-500">
            Prospect activity, intent signals, and lead scores — ordered by score
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
