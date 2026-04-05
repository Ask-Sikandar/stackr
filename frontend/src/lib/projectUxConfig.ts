export interface ProjectUxConfig {
  introMessage: string;
  assistantDisplayName?: string;
  updatedAtIso: string;
}

const KEY_PREFIX = "memox_project_ux_config_";

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function getStorageKey(projectId: number): string {
  return `${KEY_PREFIX}${projectId}`;
}

export function getProjectUxConfig(projectId: number): ProjectUxConfig | null {
  if (!isBrowser()) return null;

  const raw = localStorage.getItem(getStorageKey(projectId));
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<ProjectUxConfig>;
    return {
      introMessage: typeof parsed.introMessage === "string" ? parsed.introMessage : "",
      assistantDisplayName:
        typeof parsed.assistantDisplayName === "string" && parsed.assistantDisplayName.trim()
          ? parsed.assistantDisplayName
          : undefined,
      updatedAtIso:
        typeof parsed.updatedAtIso === "string" && parsed.updatedAtIso
          ? parsed.updatedAtIso
          : new Date().toISOString(),
    };
  } catch {
    return null;
  }
}

export function saveProjectUxConfig(
  projectId: number,
  config: Pick<ProjectUxConfig, "introMessage" | "assistantDisplayName">,
): void {
  if (!isBrowser()) return;

  const normalized: ProjectUxConfig = {
    introMessage: config.introMessage.trim(),
    assistantDisplayName: config.assistantDisplayName?.trim() || undefined,
    updatedAtIso: new Date().toISOString(),
  };

  localStorage.setItem(getStorageKey(projectId), JSON.stringify(normalized));
}
