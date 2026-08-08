import Link from "next/link";

import { Eyebrow, PageTitle } from "@/components/ui";
import { backend } from "@/lib/server-api";
import { NewProjectForm } from "./NewProjectForm";

export const dynamic = "force-dynamic";

export default async function NewProjectPage() {
  const pack = await backend.pack().catch(() => null);

  return (
    <div className="mx-auto max-w-2xl space-y-10">
      <div>
        <Link
          href="/app"
          className="eyebrow text-ink-faint transition-colors hover:text-ink"
        >
          ← Projects
        </Link>
        <div className="mt-4">
          <Eyebrow className="mb-3">New project</Eyebrow>
          <PageTitle>Point Faultline at your bot.</PageTitle>
          <p className="mt-4 max-w-xl text-lg leading-relaxed text-ink-soft">
            One project is one AI under test. It keeps your prompt, the rules you
            care about, and every run you have ever done against it — so a grade
            change means something.
          </p>
        </div>
      </div>

      {pack ? (
        <NewProjectForm rules={pack.rules} />
      ) : (
        <p className="text-sm text-ink-soft">
          Faultline&rsquo;s backend isn&rsquo;t answering right now, so the rule list
          couldn&rsquo;t load. It may be waking up — refresh in a few seconds.
        </p>
      )}
    </div>
  );
}
