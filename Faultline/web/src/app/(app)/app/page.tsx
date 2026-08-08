import Link from "next/link";

import {
  ButtonLink,
  Card,
  EmptyState,
  Eyebrow,
  Grade,
  PageTitle,
  relativeTime,
} from "@/components/ui";
import { backend, BackendError, type Project } from "@/lib/server-api";

export const dynamic = "force-dynamic";

type ProjectWithGrade = Project & { letter?: string; lastRun?: string | null };

async function withGrades(projects: Project[]): Promise<ProjectWithGrade[]> {
  // One detail call per project. Fine at the scale a single developer works at,
  // and it keeps the list honest - a card showing no grade means no grade exists,
  // rather than meaning we did not look.
  return Promise.all(
    projects.map(async (p) => {
      try {
        const detail = await backend.project(p.id);
        return {
          ...p,
          letter: detail.grades[0]?.letter,
          lastRun: detail.runs[0]?.createdAt ?? null,
        };
      } catch {
        return p;
      }
    }),
  );
}

export default async function ProjectsPage() {
  let projects: ProjectWithGrade[] = [];
  let error: string | null = null;

  try {
    const { projects: raw } = await backend.projects();
    projects = await withGrades(raw);
  } catch (e) {
    error = e instanceof BackendError ? e.message : "Could not load your projects.";
  }

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <Eyebrow className="mb-3">Your projects</Eyebrow>
          <PageTitle>What are we testing?</PageTitle>
        </div>
        {projects.length > 0 && (
          <ButtonLink href="/app/projects/new" variant="primary">
            New project
          </ButtonLink>
        )}
      </div>

      {error && (
        <Card className="px-5 py-4">
          <p className="text-sm text-ink-soft">{error}</p>
        </Card>
      )}

      {!error && projects.length === 0 && (
        <EmptyState
          title="Nothing under test yet."
          action={
            <ButtonLink href="/app/projects/new" variant="primary">
              Add your first project
            </ButtonLink>
          }
        >
          Paste the system prompt your AI runs on. Faultline writes adversarial tests
          against it, grades what comes back, and tracks whether each change makes
          your bot safer or more exposed.
        </EmptyState>
      )}

      {projects.length > 0 && (
        <ul className="grid gap-4 sm:grid-cols-2">
          {projects.map((project) => (
            <li key={project.id}>
              <Link
                href={`/app/projects/${project.id}`}
                className="group block h-full border border-rule bg-paper-raised p-5 transition-colors hover:border-ink-faint"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="font-display text-lg leading-tight tracking-tight">
                      {project.name}
                    </p>
                    <p className="eyebrow mt-2 text-ink-faint">
                      {project.ruleIds.length} rule
                      {project.ruleIds.length === 1 ? "" : "s"} ·{" "}
                      {project.lastRun
                        ? `last run ${relativeTime(project.lastRun)}`
                        : "never run"}
                    </p>
                  </div>
                  <Grade letter={project.letter ?? "-"} />
                </div>
                <p className="mt-4 line-clamp-2 text-sm leading-relaxed text-ink-soft">
                  {project.promptPreview || "No prompt stored."}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
