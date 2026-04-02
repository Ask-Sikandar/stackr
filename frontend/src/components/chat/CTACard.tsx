"use client";

import { useState } from "react";

interface CTACardProps {
  label: string;
  description: string;
}

export function CTACard({ label, description }: CTACardProps) {
  const [submitted, setSubmitted] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [showForm, setShowForm] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // In production, POST to /api/leads/handoff/ — for POC we just confirm
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="rounded-xl border border-green-200 bg-green-50 p-4 text-center">
        <p className="text-sm font-semibold text-green-700">
          Request received! Our sales team will reach out within 24 hours.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-orange-200 bg-orange-50 p-4">
      <p className="text-sm font-semibold text-gray-800">{description}</p>
      {!showForm ? (
        <button
          onClick={() => setShowForm(true)}
          className="mt-3 w-full rounded-lg bg-orange-500 px-4 py-2 text-sm font-bold text-white shadow-sm hover:bg-orange-600 transition-colors"
        >
          {label}
        </button>
      ) : (
        <form onSubmit={handleSubmit} className="mt-3 space-y-2">
          <input
            required
            type="text"
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
          />
          <input
            required
            type="email"
            placeholder="Your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
          />
          <button
            type="submit"
            className="w-full rounded-lg bg-orange-500 px-4 py-2 text-sm font-bold text-white hover:bg-orange-600 transition-colors"
          >
            Submit Request
          </button>
        </form>
      )}
    </div>
  );
}
