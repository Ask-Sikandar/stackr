export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-50 p-6 md:p-10">
      <div className="mx-auto max-w-5xl">
        <header className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm md:p-12">
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">Memox Portal</p>
          <h1 className="mt-2 text-4xl font-extrabold text-slate-900 md:text-5xl">Pacific Container Co. AI Workspace</h1>
          <p className="mt-4 max-w-2xl text-slate-600">
            Manage organizations and projects, ingest sales documents, monitor leads, and run tenant-scoped chat.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <a href="/signup" className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700">
              Create account
            </a>
            <a href="/login" className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Log in
            </a>
            <a href="/portal" className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Open portal
            </a>
          </div>
        </header>

        <section className="mt-6 grid gap-4 md:grid-cols-3">
          <a href="/chat" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:border-blue-300">
            <h2 className="text-lg font-semibold text-slate-900">Project Chat</h2>
            <p className="mt-1 text-sm text-slate-500">Tenant-scoped websocket assistant.</p>
          </a>
          <a href="/admin/documents" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:border-blue-300">
            <h2 className="text-lg font-semibold text-slate-900">Documents</h2>
            <p className="mt-1 text-sm text-slate-500">Upload and ingest project docs.</p>
          </a>
          <a href="/admin/leads" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:border-blue-300">
            <h2 className="text-lg font-semibold text-slate-900">Lead Dashboard</h2>
            <p className="mt-1 text-sm text-slate-500">Track scores and intent events.</p>
          </a>
        </section>
      </div>
    </main>
  );
}
