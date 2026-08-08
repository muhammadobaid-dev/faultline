"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, Card, Eyebrow, Notice } from "@/components/ui";
import { useToast } from "@/components/Toast";
import type { Rule } from "@/lib/server-api";

const MIN_PROMPT = 20;

export function NewProjectForm({ rules }: { rules: Rule[] }) {
  const router = useRouter();
  const { push } = useToast();
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [selected, setSelected] = useState<string[]>(rules.map((r) => r.id));
  const [saving, setSaving] = useState(false);

  const promptTooShort = prompt.trim().length < MIN_PROMPT;
  const canSubmit = name.trim().length > 0 && !promptTooShort && !saving;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    setSaving(true);
    try {
      const response = await fetch("/api/faultline/projects", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          system_prompt: prompt,
          rule_ids: selected,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "Could not create the project.");
      }
      const project = await response.json();
      router.push(`/app/projects/${project.id}`);
    } catch (e) {
      push({
        tone: "attention",
        title: "Couldn't create that project.",
        detail: e instanceof Error ? e.message : "Try again in a moment.",
      });
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-8">
      <div className="space-y-2">
        <label htmlFor="name" className="eyebrow block text-ink-faint">
          What is it called?
        </label>
        <input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={80}
          required
          placeholder="Checkout support bot"
          className="w-full border border-rule bg-paper-raised px-4 py-3 text-base outline-none placeholder:text-ink-faint focus:border-ink-faint"
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="prompt" className="eyebrow block text-ink-faint">
          Paste its system prompt
        </label>
        <textarea
          id="prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={12}
          required
          spellCheck={false}
          placeholder={
            "You are the support assistant for…\n\nInclude the internal notes you would not want a customer to see — that is exactly what Faultline tries to pull out."
          }
          className="w-full resize-y border border-rule bg-paper-raised px-4 py-3 font-mono text-sm leading-relaxed outline-none placeholder:text-ink-faint focus:border-ink-faint"
          aria-describedby="prompt-help"
        />
        <p id="prompt-help" className="text-xs leading-relaxed text-ink-faint">
          {prompt.length.toLocaleString()} characters. Stored encrypted at rest and
          never shown on any public page.
          {promptTooShort && prompt.length > 0 && (
            <span className="text-amber-text"> Needs at least {MIN_PROMPT}.</span>
          )}
        </p>
      </div>

      <fieldset className="space-y-3">
        <legend className="eyebrow text-ink-faint">What should we test for?</legend>
        <div className="grid gap-2 sm:grid-cols-2">
          {rules.map((rule) => {
            const on = selected.includes(rule.id);
            return (
              <button
                key={rule.id}
                type="button"
                aria-pressed={on}
                onClick={() =>
                  setSelected((s) =>
                    s.includes(rule.id)
                      ? s.filter((r) => r !== rule.id)
                      : [...s, rule.id],
                  )
                }
                className={`border px-3 py-2.5 text-left text-sm transition-[border-color] cursor-pointer ${
                  on
                    ? "border-ink bg-ink text-paper"
                    : "border-rule text-ink-soft hover:border-ink-faint"
                }`}
              >
                <span className="font-mono text-[0.625rem] tracking-widest opacity-70">
                  {rule.id}
                </span>
                <span className="block leading-snug">{rule.title}</span>
              </button>
            );
          })}
        </div>
        {selected.length === 0 && (
          <Notice tone="warn">
            Nothing selected — we&rsquo;ll test every rule in the pack.
          </Notice>
        )}
      </fieldset>

      <Card className="px-5 py-4">
        <Eyebrow className="mb-2">Before you run it</Eyebrow>
        <p className="text-sm leading-relaxed text-ink-soft">
          Faultline runs your prompt on its own model to play the part of your bot.
          That tests the prompt, not your live deployment, so a result here can point
          you at a weakness but cannot back a public claim about your production
          system.
        </p>
      </Card>

      <div className="flex items-center gap-4">
        <Button type="submit" variant="primary" disabled={!canSubmit}>
          {saving ? "Creating…" : "Create project"}
        </Button>
        <span className="text-xs text-ink-faint">
          Nothing runs until you say so.
        </span>
      </div>
    </form>
  );
}
