import "server-only";

import { auth } from "@/auth";
import type { Coverage } from "@/components/CoveragePanel";
import type { Failure } from "./types";

/**
 * Server-side access to the backend.
 *
 * Server components call this directly rather than going through the browser proxy:
 * one hop instead of two, and the page renders with data already in hand instead of
 * flashing a skeleton. The internal token and the user id are attached here and
 * never leave the server.
 */

const BACKEND =
  process.env.FAULTLINE_API_URL?.replace(/\/$/, "") ??
  "https://faultline-api-pwl3.onrender.com";

export type Rule = {
  id: string;
  title: string;
  rule: string;
  inPunchbag: boolean;
};

export type Pack = {
  id: string;
  name: string;
  version: number;
  summary: string;
  rules: Rule[];
};

export type Project = {
  id: string;
  name: string;
  targetKind: string;
  targetModel: string;
  ruleIds: string[];
  isSimulated: boolean;
  createdAt: string;
  updatedAt: string;
  promptPreview: string;
};

export type RunSummary = {
  id: string;
  status: string;
  size: string;
  testSetVersion: string | null;
  done: number;
  total: number;
  stage: string;
  createdAt: string | null;
  finishedAt: string | null;
  error: string | null;
  failureCount: number;
};

export type GradeRow = {
  dimension: string;
  letter: string;
  failureRate: number;
  graded: number;
  failures: number;
  incomplete: number;
  size: string;
  runId: string;
  at: string | null;
};

export type TrendPoint = GradeRow & { testSetVersion: string | null };

export type ProjectDetail = {
  project: Project;
  runs: RunSummary[];
  grades: GradeRow[];
  trend: TrendPoint[];
  sizes: { smoke: number; full: number };
};

export type RunResult = {
  pack: { id: string; name: string; version: number };
  target: { id: string; name: string };
  judge: string;
  graded: number;
  passes: number;
  flagged: number;
  incomplete: number;
  degraded: boolean;
  failures: Failure[];
  grades?: {
    dimension: string;
    letter: string;
    reason: string;
    failureRate: number;
    graded: number;
    failures: number;
    incomplete: number;
  }[];
  testSetVersion?: string | null;
  isSimulated?: boolean;
  // Confidence in the assessment, deliberately separate from the grade.
  coverage?: Coverage;
};

export type Run = {
  id: string;
  status: string;
  stage: string;
  done: number;
  total: number;
  percent: number;
  result: RunResult | null;
  error: string | null;
  project_id: string | null;
};

export class BackendError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function call<T>(
  path: string,
  init: RequestInit = {},
  { authenticated = true }: { authenticated?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  const token = process.env.FAULTLINE_INTERNAL_TOKEN;
  if (token) headers["x-faultline-token"] = token;

  if (authenticated) {
    const session = await auth();
    if (!session?.user?.id) throw new BackendError("Not signed in.", 401);
    headers["x-faultline-user"] = session.user.id;
  }

  let response: Response;
  try {
    response = await fetch(`${BACKEND}${path}`, {
      ...init,
      headers: { ...headers, ...(init.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new BackendError(
      "Faultline's backend isn't answering. It may be waking up.",
      503,
    );
  }

  if (response.status === 204) return undefined as T;
  if (!response.ok) {
    const detail = await response
      .json()
      .then((b) => (typeof b?.detail === "string" ? b.detail : null))
      .catch(() => null);
    throw new BackendError(detail ?? "Something went wrong.", response.status);
  }
  return response.json() as Promise<T>;
}

export const backend = {
  pack: () => call<Pack>("/packs", {}, { authenticated: false }),
  projects: () => call<{ projects: Project[] }>("/projects"),
  project: (id: string) => call<ProjectDetail>(`/projects/${id}`),
  run: (id: string) => call<Run>(`/runs/${id}`, {}, { authenticated: false }),
};
