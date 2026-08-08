import { handlers } from "@/auth";

// The pg driver needs the Node runtime; the edge runtime has no TCP sockets.
export const runtime = "nodejs";

export const { GET, POST } = handlers;
