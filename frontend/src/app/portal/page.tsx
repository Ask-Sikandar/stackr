"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/lib/api";
import {
  clearAuthSession,
  getOrganizationId,
  getProjectId,
  setOrganizationId,
  setProjectId,
} from "@/lib/session";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import type { Document, Organization, Project } from "@/types";

type DocList = Document[] | { results: Document[] };

function normalizeDocs(payload: DocList): Document[] {
  return Array.isArray(payload) ? payload : payload.results ?? [];
}

export default function PortalPage() {
  const router = useRouter();
  const { isCheckingAuth, isAuthenticated } = useAuthGuard();

  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<number | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [orgName, setOrgName] = useState("");
  const [projectName, setProjectName] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingOrg, setSavingOrg] = useState(false);
  const [savingProject, setSavingProject] = useState(false);
  const [checkingChatAccess, setCheckingChatAccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOrganizations = useCallback(async () => {
    const orgs = await apiFetch<Organization[]>("/api/accounts/organizations/");
    setOrganizations(orgs);

    const persistedOrg = getOrganizationId();
    const orgFromStorage = orgs.find((o) => o.id === persistedOrg);
    const activeOrg = orgFromStorage ?? orgs[0] ?? null;

    if (activeOrg) {
      setSelectedOrgId(activeOrg.id);
      setOrganizationId(activeOrg.id);
    } else {
      setSelectedOrgId(null);
    }
  }, []);

  const loadProjects = useCallback(async (organizationId: number) => {
    const response = await apiFetch<Project[]>(`/api/accounts/projects/?organization_id=${organizationId}`);
    setProjects(response);

    const persistedProject = getProjectId();
    const fromStorage = response.find((p) => p.id === persistedProject);
    const active = fromStorage ?? response[0] ?? null;
    if (active) {
      setSelectedProjectId(active.id);
      setProjectId(active.id);
    } else {
      setSelectedProjectId(null);
    }
  }, []);

  useEffect(() => {
    if (isCheckingAuth || !isAuthenticated) return;

    (async () => {
      setLoading(true);
      setError(null);
      try {
        await loadOrganizations();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load organizations");
      } finally {
        setLoading(false);
      }
    })();
  }, [isAuthenticated, isCheckingAuth, loadOrganizations]);

  useEffect(() => {
    if (!selectedOrgId) return;
    (async () => {
      try {
        await loadProjects(selectedOrgId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load projects");
      }
    })();
  }, [selectedOrgId, loadProjects]);

  const createOrganization = async (e: FormEvent) => {
    e.preventDefault();
    if (!orgName.trim()) return;
    setSavingOrg(true);
    setError(null);

    try {
      const org = await apiFetch<Organization>("/api/accounts/organizations/", {
        method: "POST",
        body: JSON.stringify({
          name: orgName.trim(),
          use_private_llm_credentials: false,
          allow_platform_fallback: true,
        }),
      });
      setOrganizations((prev) => [org, ...prev]);
      setSelectedOrgId(org.id);
      setOrganizationId(org.id);
      setOrgName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create organization");
    } finally {
      setSavingOrg(false);
    }
  };

  const createProject = async (e: FormEvent) => {
    e.preventDefault();
    if (!projectName.trim() || !selectedOrgId) return;

    setSavingProject(true);
    setError(null);
    try {
      const project = await apiFetch<Project>("/api/accounts/projects/", {
        method: "POST",
        body: JSON.stringify({
          organization_id: selectedOrgId,
          name: projectName.trim(),
          llm_primary_provider: "ollama",
          llm_backup_provider: "",
          custom_instructions: "",
        }),
      });

      setProjects((prev) => [project, ...prev]);
      setSelectedProjectId(project.id);
      setProjectId(project.id);
      setProjectName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setSavingProject(false);
    }
  };

  const handleSignOut = () => {
    clearAuthSession();
    router.push("/login");
  };

  const handleOpenChat = async () => {
    if (!selectedProjectId) {
      setError("Create or select a project before opening chat.");
      return;
    }

    setCheckingChatAccess(true);
    setError(null);

    try {
      const docs = await apiFetch<DocList>("/api/documents/");
      const hasIngestedDoc = normalizeDocs(docs).some(
        (doc) => doc.project_id === selectedProjectId && doc.processed,
      );

      if (!hasIngestedDoc) {
        setError("Ingest at least one document for this project before opening chat.");
        router.push("/admin/documents");
        return;
      }

      router.push("/chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to verify chat prerequisites");
    } finally {
      setCheckingChatAccess(false);
    }
  };

  if (isCheckingAuth || !isAuthenticated || loading) {
    return <main className="min-h-screen bg-slate-50 p-8 text-slate-500">Loading portal...</main>;
  }

  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Portal</h1>
            <p className="text-sm text-slate-500">Manage organizations, projects, and operations.</p>
          </div>
          <button
            onClick={handleSignOut}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            Sign out
          </button>
        </header>

        {error && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</p>}

        <div className="grid gap-6 md:grid-cols-2">
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Organizations</h2>
            <form onSubmit={createOrganization} className="mt-3 flex gap-2">
              <input
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                placeholder="New organization"
                className="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm"
              />
              <button
                type="submit"
                disabled={savingOrg}
                className="rounded-xl bg-blue-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {savingOrg ? "Saving..." : "Create"}
              </button>
            </form>

            <div className="mt-4 space-y-2">
              {organizations.map((org) => (
                <button
                  key={org.id}
                  onClick={() => {
                    setSelectedOrgId(org.id);
                    setOrganizationId(org.id);
                  }}
                  className={`w-full rounded-xl border px-3 py-2 text-left text-sm ${
                    selectedOrgId === org.id
                      ? "border-blue-500 bg-blue-50 text-blue-700"
                      : "border-slate-200 bg-white text-slate-700"
                  }`}
                >
                  {org.name}
                </button>
              ))}
              {organizations.length === 0 && (
                <p className="text-sm text-slate-500">No organizations yet. Create your first one.</p>
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Projects</h2>
            <form onSubmit={createProject} className="mt-3 flex gap-2">
              <input
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="New project"
                className="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm"
              />
              <button
                type="submit"
                disabled={savingProject || !selectedOrgId}
                className="rounded-xl bg-blue-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {savingProject ? "Saving..." : "Create"}
              </button>
            </form>

            <div className="mt-4 space-y-2">
              {projects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => {
                    setSelectedProjectId(project.id);
                    setProjectId(project.id);
                  }}
                  className={`w-full rounded-xl border px-3 py-2 text-left text-sm ${
                    selectedProjectId === project.id
                      ? "border-blue-500 bg-blue-50 text-blue-700"
                      : "border-slate-200 bg-white text-slate-700"
                  }`}
                >
                  <span className="font-medium">{project.name}</span>
                  <span className="ml-2 text-xs text-slate-500">{project.llm_primary_provider}</span>
                </button>
              ))}
              {projects.length === 0 && (
                <p className="text-sm text-slate-500">No projects for this organization yet.</p>
              )}
            </div>
          </section>
        </div>

        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Workspace</h2>
          <p className="mt-1 text-sm text-slate-500">Choose where to continue once a project is selected.</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              onClick={handleOpenChat}
              disabled={checkingChatAccess}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-500"
            >
              {checkingChatAccess ? "Checking prerequisites..." : "Open Chat"}
            </button>
            <a href="/admin/documents" className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Documents
            </a>
            <a href="/admin/leads" className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Leads
            </a>
          </div>
        </section>
      </div>
    </main>
  );
}
