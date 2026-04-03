const ACCESS_TOKEN_KEY = "memox_access_token";
const REFRESH_TOKEN_KEY = "memox_refresh_token";
const ORG_ID_KEY = "memox_org_id";
const PROJECT_ID_KEY = "memox_project_id";

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function saveAuthSession(access: string, refresh: string, organizationId?: number | null): void {
  if (!isBrowser()) return;
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  if (typeof organizationId === "number") {
    localStorage.setItem(ORG_ID_KEY, String(organizationId));
  }
}

export function clearAuthSession(): void {
  if (!isBrowser()) return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(ORG_ID_KEY);
  localStorage.removeItem(PROJECT_ID_KEY);
}

export function getAccessToken(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getOrganizationId(): number | null {
  if (!isBrowser()) return null;
  const raw = localStorage.getItem(ORG_ID_KEY);
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

export function setOrganizationId(id: number): void {
  if (!isBrowser()) return;
  localStorage.setItem(ORG_ID_KEY, String(id));
}

export function getProjectId(): number | null {
  if (!isBrowser()) return null;
  const raw = localStorage.getItem(PROJECT_ID_KEY);
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

export function setProjectId(id: number): void {
  if (!isBrowser()) return;
  localStorage.setItem(PROJECT_ID_KEY, String(id));
}
