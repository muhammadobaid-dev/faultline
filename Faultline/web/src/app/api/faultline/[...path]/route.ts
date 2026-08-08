import { NextRequest } from "next/server";

import { auth } from "@/auth";

/**
 * Same-origin proxy to the FastAPI backend.
 *
 * Three jobs. It removes CORS entirely. It resolves the backend URL at request time
 * on the server, so a deploy with an unset variable cannot ship a client pointing at
 * localhost. And it is where identity is asserted: the session is read here and the
 * user id forwarded alongside a shared secret, so the backend can trust the caller
 * without the browser ever holding the token.
 */

const BACKEND =
  process.env.FAULTLINE_API_URL?.replace(/\/$/, "") ??
  "https://faultline-api-pwl3.onrender.com";

// Every proxied call is a quick enqueue or status read; the long work happens in
// the backend's worker. Comfortably inside Vercel's function ceiling.
export const maxDuration = 30;

async function forward(request: NextRequest, path: string[]) {
  const target = `${BACKEND}/${path.join("/")}${request.nextUrl.search}`;

  const headers: Record<string, string> = { "content-type": "application/json" };
  const token = process.env.FAULTLINE_INTERNAL_TOKEN;
  if (token) headers["x-faultline-token"] = token;

  const session = await auth();
  if (session?.user?.id) headers["x-faultline-user"] = session.user.id;

  // Per-IP limits live on the backend, so the caller's address has to survive the
  // hop rather than every visitor looking like Vercel.
  const forwardedFor =
    request.headers.get("x-forwarded-for") ?? request.headers.get("x-real-ip");
  if (forwardedFor) headers["x-forwarded-for"] = forwardedFor;

  const body =
    request.method === "POST" || request.method === "DELETE"
      ? await request.text()
      : undefined;

  try {
    const response = await fetch(target, {
      method: request.method,
      headers,
      body: body || undefined,
      cache: "no-store",
    });
    const text = await response.text();
    return new Response(text || null, {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    // Render's free instance sleeps after fifteen minutes and wakes in tens of
    // seconds. 503 tells the client this is worth waiting out.
    return Response.json(
      { detail: "Faultline's backend isn't answering. It may be waking up." },
      { status: 503 },
    );
  }
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: Ctx) {
  return forward(request, (await params).path);
}

export async function POST(request: NextRequest, { params }: Ctx) {
  return forward(request, (await params).path);
}

export async function DELETE(request: NextRequest, { params }: Ctx) {
  return forward(request, (await params).path);
}
