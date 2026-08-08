import PostgresAdapter from "@auth/pg-adapter";
import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";

import { pool } from "@/lib/pool";

/**
 * GitHub is the only sign-in, deliberately.
 *
 * The audience is developers, they already have a GitHub account, and the CI
 * integration needs that connection anyway. It also means Faultline never stores a
 * password: no reset flow, no credential-stuffing surface, and a whole category of
 * things to get wrong simply does not exist.
 *
 * Sessions live in Postgres rather than in a JWT so that signing out actually ends
 * the session server-side, and so a revoked account stops working immediately
 * instead of at the next token expiry.
 */
export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: PostgresAdapter(pool),
  providers: [GitHub],
  session: { strategy: "database" },
  pages: { signIn: "/signin" },
  callbacks: {
    session({ session, user }) {
      // The user id is what every project row is keyed by, so it has to be on the
      // session rather than looked up again on each request.
      if (session.user) session.user.id = user.id;
      return session;
    },
  },
});
