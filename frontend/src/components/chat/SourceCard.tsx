"use client";

import { useState } from "react";
import type { Source } from "@/types";

interface SourceCardProps {
  source: Source;
}

export function SourceCard({ source }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);
  const relevancePct = Math.round(source.score * 100);
  const badgeColor =
    relevancePct >= 85 ? "bg-green-100 text-green-700" : relevancePct >= 60 ? "bg-yellow-100 text-yellow-700" : "bg-gray-100 text-gray-600";

  return (
    <button
      onClick={() => setExpanded((v) => !v)}
      className="w-full text-left rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm transition-colors hover:bg-gray-100"
      aria-expanded={expanded}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-gray-700 truncate">{source.title}</span>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${badgeColor}`}>
          {relevancePct}% match
        </span>
      </div>
      {expanded && (
        <p className="mt-2 text-gray-600 leading-snug line-clamp-4">{source.excerpt}</p>
      )}
    </button>
  );
}
