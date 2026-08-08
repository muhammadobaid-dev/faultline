import type { Failure } from "./types";

// Same-origin. The proxy in app/api/faultline resolves the real backend at request
// time on the server, so no backend URL is baked into this bundle and there is no
// cross-origin call to permit.
const BASE = "/api/faultline";

export type RunStatus =
  | "queued"
  | "running"
  | "done"
  | "failed"
  | "deferred"
  | "cancelled";

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
};

export type Run = {
  id: string;
  status: RunStatus;
  stage: string;
  done: number;
  total: number;
  percent: number;
  result: RunResult | null;
  error: string | null;
  replay_of: string | null;
};

export type Rule = { id: string; title: string; rule: string };
export type Pack = {
  id: string;
  name: string;
  version: number;
  summary: string;
  rules: Rule[];
};

/** Carries the plain-English reason a request failed, ready for a toast. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly retryable: boolean,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    // The service may be asleep - on Render a cold start takes tens of seconds -
    // so this is worth retrying rather than reporting as broken.
    throw new ApiError(
      "Faultline's backend isn't answering. It may be waking up.",
      0,
      true,
    );
  }

  if (!response.ok) {
    const detail = await response
      .json()
      .then((b) => (typeof b?.detail === "string" ? b.detail : null))
      .catch(() => null);
    throw new ApiError(
      detail ?? "Something went wrong on our side.",
      response.status,
      response.status >= 500,
    );
  }
  return response.json() as Promise<T>;
}

export const api = {
  packs: () => request<Pack>("/packs"),
  startPunchbagRun: (ruleIds: string[], count: number) =>
    request<Run>("/punchbag/runs", {
      method: "POST",
      body: JSON.stringify({ rule_ids: ruleIds, count }),
    }),
  run: (id: string) => request<Run>(`/runs/${id}`),
  cancel: (id: string) =>
    request<Run>(`/runs/${id}/cancel`, { method: "POST" }),
};
