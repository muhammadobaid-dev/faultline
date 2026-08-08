import { redirect } from "next/navigation";
import Link from "next/link";

import { auth, signIn } from "@/auth";
import { Button, Eyebrow } from "@/components/ui";

export default async function SignInPage() {
  const session = await auth();
  if (session?.user) redirect("/app");

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="border-b border-rule">
        <div className="mx-auto max-w-6xl px-6 py-4 md:px-10">
          <Link href="/" className="font-display text-lg font-semibold tracking-tight">
            Faultline
          </Link>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-6 py-20">
        <Eyebrow className="mb-4">Sign in</Eyebrow>
        <h1 className="font-display text-3xl font-semibold leading-tight tracking-tight text-balance">
          Keep your results, not just your last run.
        </h1>
        <p className="mt-4 text-base leading-relaxed text-ink-soft">
          Signing in gives you projects that remember your prompt, the attacks pinned
          against it, and every grade over time — so you can see whether a change made
          your AI safer or opened something up.
        </p>

        <form
          className="mt-8"
          action={async () => {
            "use server";
            await signIn("github", { redirectTo: "/app" });
          }}
        >
          <Button type="submit" variant="primary" className="w-full py-3">
            Continue with GitHub
          </Button>
        </form>

        <p className="mt-6 text-xs leading-relaxed text-ink-faint">
          GitHub is the only sign-in, on purpose: you already have an account, the CI
          integration needs that connection anyway, and it means Faultline never
          stores a password.
        </p>

        <p className="mt-10 text-sm text-ink-soft">
          Just looking?{" "}
          <Link href="/" className="underline underline-offset-4">
            Try the punchbag
          </Link>{" "}
          — no account needed.
        </p>

        <p className="mt-16 eyebrow text-ink-soft">Developed by MUHAMMAD OBAID</p>
      </main>
    </div>
  );
}
