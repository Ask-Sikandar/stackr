"use client";

import type { Lead, IntentEvent } from "@/types";

const INTENT_COLORS: Record<string, string> = {
  pricing: "bg-blue-100 text-blue-700",
  availability: "bg-purple-100 text-purple-700",
  conversion: "bg-orange-100 text-orange-700",
  general: "bg-gray-100 text-gray-600",
};

const SCORE_COLOR = (score: number) => {
  if (score >= 30) return "text-orange-600 font-bold";
  if (score >= 15) return "text-blue-600 font-semibold";
  return "text-gray-500";
};

function IntentTimeline({ events }: { events: IntentEvent[] }) {
  if (!events?.length) return <p className="text-xs text-gray-400">No activity yet</p>;
  return (
    <div className="flex flex-wrap gap-1">
      {events.map((ev, i) => (
        <span
          key={i}
          title={`${ev.message_preview} (+${ev.score_delta}pts)`}
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${INTENT_COLORS[ev.intent] ?? "bg-gray-100 text-gray-600"}`}
        >
          {ev.intent}
        </span>
      ))}
    </div>
  );
}

interface LeadDashboardProps {
  leads: Lead[];
}

export function LeadDashboard({ leads }: LeadDashboardProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
          <tr>
            <th className="px-4 py-3 text-left">Lead ID</th>
            <th className="px-4 py-3 text-center">Score</th>
            <th className="px-4 py-3 text-center">Messages</th>
            <th className="px-4 py-3 text-left">Intent Journey</th>
            <th className="px-4 py-3 text-left">Last Seen</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {leads.map((lead) => (
            <tr key={lead.lead_id} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-mono text-xs text-gray-600">
                {lead.lead_id.slice(0, 8)}...
              </td>
              <td className={`px-4 py-3 text-center text-base ${SCORE_COLOR(lead.score)}`}>
                {lead.score}
              </td>
              <td className="px-4 py-3 text-center text-gray-600">{lead.message_count}</td>
              <td className="px-4 py-3">
                <IntentTimeline events={lead.intent_events ?? []} />
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs">
                {new Date(lead.last_seen_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {leads.length === 0 && (
        <div className="py-12 text-center text-gray-400">No leads yet. Start a conversation!</div>
      )}
    </div>
  );
}
