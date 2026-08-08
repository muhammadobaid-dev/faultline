import Link from "next/link";
import { redirect } from "next/navigation";

import { auth, signOut } from "@/auth";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ToastProvider } from "@/components/Toast";

/**
 * The signed-in shell.
 *
 * Guarding here rather than in each page means a new screen is protected by
 * existing, not by remembering to add a check.
 */
export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();
  if (!session?.user) redirect("/signin");

  const name = session.user.name ?? session.user.email ?? "your account";

  return (
    <ToastProvider>
      <div className="flex min-h-full flex-1 flex-col">
        <header className="border-b border-rule">
          <div className="mx-auto flex max-w-6xl items-baseline justify-between gap-6 px-6 py-4 md:px-10">
            <nav className="flex items-baseline gap-6">
              <Link href="/app" className="font-display text-lg font-semibold tracking-tight">
                Faultline
              </Link>
              <Link
                href="/app"
                className="eyebrow text-ink-faint transition-colors hover:text-ink"
              >
                Projects
              </Link>
              <Link
                href="/"
                className="eyebrow hidden text-ink-faint transition-colors hover:text-ink sm:inline"
              >
                Punchbag
              </Link>
            </nav>

            <div className="flex items-baseline gap-5">
              <span className="eyebrow hidden text-ink-faint md:inline" title={name}>
                {name}
              </span>
              <ThemeToggle />
              <form
                action={async () => {
                  "use server";
                  await signOut({ redirectTo: "/" });
                }}
              >
                <button
                  type="submit"
                  className="eyebrow cursor-pointer text-ink-faint transition-colors hover:text-ink"
                >
                  Sign out
                </button>
              </form>
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10 md:px-10 md:py-14">
          {children}
        </main>

        <footer className="border-t border-rule">
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-6 md:flex-row md:items-baseline md:justify-between md:px-10">
            <p className="font-mono text-xs leading-relaxed text-ink-faint">
              Grades come from a single-family Gemini judge whose agreement with human
              labels is measured, not assumed.
            </p>
            <p className="eyebrow shrink-0 text-ink-soft">
              Developed by MUHAMMAD OBAID
            </p>
          </div>
        </footer>
      </div>
    </ToastProvider>
  );
}
