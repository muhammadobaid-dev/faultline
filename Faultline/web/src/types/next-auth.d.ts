import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    user: {
      /** Every project row is keyed by this, so it is required rather than optional. */
      id: string;
    } & DefaultSession["user"];
  }
}
