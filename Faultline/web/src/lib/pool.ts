import { Pool } from "pg";

/**
 * Postgres pool for Auth.js and for reads the frontend does directly.
 *
 * Kept small on purpose. Vercel runs each request in its own short-lived instance,
 * so a large pool per instance multiplies into Neon's connection ceiling under any
 * real concurrency. Three is enough for a request that reads a session and a page
 * of rows, and idle connections are dropped quickly so a sleeping instance holds
 * nothing open.
 */

const globalForPool = globalThis as unknown as { faultlinePool?: Pool };

export const pool =
  globalForPool.faultlinePool ??
  new Pool({
    connectionString: process.env.FAULTLINE_DATABASE_URL,
    max: 3,
    idleTimeoutMillis: 10_000,
    connectionTimeoutMillis: 15_000,
    // Neon terminates unencrypted connections. The certificate chain is public
    // so verification adds nothing here beyond a bundled CA dependency.
    ssl: { rejectUnauthorized: false },
  });

// Reused across hot reloads in development, so a file save does not leak a pool.
if (process.env.NODE_ENV !== "production") globalForPool.faultlinePool = pool;
