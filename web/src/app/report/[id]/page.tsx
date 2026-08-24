"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { SiteHeader } from "@/components/SiteHeader";
import { RubricBars, RubricTable } from "@/components/Rubric";
import { Button } from "@/components/ui";
import { claimSession, getReport, retrySession } from "@/lib/api";
import { getBypassToken } from "@/lib/auth";
import type { Feedback } from "@/lib/types";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<Awaited<ReturnType<typeof getReport>> | null>(null);
  const [open, setOpen] = useState<number | null>(0);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!id) return;
    getReport(id).then(setData);
  }, [id]);

  if (!data) {
    return (
      <div>
        <SiteHeader />
        <main className="mx-auto max-w-4xl px-4 py-10">Loading report…</main>
      </div>
    );
  }
  const report: Feedback = data.report;
  const tech = report.rubric.technical_correctness;
  const reason = report.rubric.technical_reasoning;
  const markdown = buildMarkdown(data);

  return (
    <div>
      <SiteHeader />
      <main className="mx-auto max-w-4xl px-4 py-10">
        <p className="text-sm text-muted-foreground">
          {data.config.interview_type} · {data.plan.resolved_mode} · {data.plan.resolved_difficulty}
        </p>
        <h1 className="mt-2 text-3xl font-semibold">Debrief</h1>
        <p className="mt-4 text-4xl font-semibold" data-testid="overall-score">{report.overall_score}/100</p>
        <p className="mt-3 max-w-2xl text-muted-foreground">{report.overall_summary}</p>

        <section className="mt-10">
          <h2 className="text-xl font-semibold">Qualitative rubric</h2>
          <div className="mt-4 rounded-lg border border-border bg-card p-5">
            <RubricBars report={report} />
          </div>
        </section>

        <section className="mt-8 grid gap-4 sm:grid-cols-2">
          <div className="rounded-lg border border-border bg-card p-5">
            <h3 className="font-semibold">Technical correctness</h3>
            <p className="mt-2 text-2xl">
              {tech?.assessed && tech.score != null ? `${tech.score}/5` : "Not assessed"}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">{tech?.feedback}</p>
          </div>
          <div className="rounded-lg border border-border bg-card p-5">
            <h3 className="font-semibold">Technical reasoning</h3>
            <p className="mt-2 text-2xl">
              {reason?.assessed && reason.score != null ? `${reason.score}/5` : "Not assessed"}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">{reason?.feedback}</p>
          </div>
        </section>

        <RubricTable report={report} />

        <section className="mt-10">
          <h2 className="text-xl font-semibold">Question review</h2>
          <div className="mt-4 space-y-2">
            {report.question_reviews.map((review) => (
              <details
                key={review.question_id}
                open={open === review.question_index}
                onToggle={(e) => {
                  if ((e.target as HTMLDetailsElement).open) setOpen(review.question_index);
                }}
                className="rounded-lg border border-border bg-card p-4"
              >
                <summary className="cursor-pointer font-medium">
                  Q{review.question_index + 1} · {review.question_type}
                  {review.source === "voice" ? " · voice" : ""}
                </summary>
                <p className="mt-3">{review.what_went_well}</p>
                <p className="mt-2 text-sm text-muted-foreground">{review.what_to_improve}</p>
                {review.correct_answer_if_applicable ? (
                  <p className="mt-2 text-sm">
                    Correct answer: {review.correct_answer_if_applicable}
                  </p>
                ) : null}
              </details>
            ))}
          </div>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-semibold">Improved answer</h2>
          <p className="mt-2 text-sm text-muted-foreground">{report.improved_answer.original_question}</p>
          <p className="mt-3 rounded-lg border border-border bg-card p-4">{report.improved_answer.rewrite}</p>
          <p className="mt-2 text-sm text-muted-foreground">{report.improved_answer.what_changed}</p>
        </section>

        <section className="mt-10">
          <h2 className="text-xl font-semibold">Drills</h2>
          <ul className="mt-4 space-y-3">
            {report.targeted_drills.map((drill) => (
              <li key={drill.drill} className="rounded-lg border border-border bg-card p-4">
                <p className="font-medium">{drill.drill}</p>
                <p className="mt-1 text-sm text-muted-foreground">{drill.why_this_helps}</p>
              </li>
            ))}
          </ul>
        </section>

        {report.coaching_notes.length ? (
          <ul className="mt-8 list-disc pl-5 text-sm text-muted-foreground">
            {report.coaching_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        ) : null}

        <div className="mt-10 flex flex-wrap gap-3">
          <a
            href={`data:text/markdown;charset=utf-8,${encodeURIComponent(markdown)}`}
            download="interviewos-report.md"
            className="inline-flex cursor-pointer items-center rounded-md border border-border px-4 py-2 text-sm"
          >
            Download report
          </a>
          <Button
            variant="ghost"
            onClick={async () => {
              const created = await retrySession(data.id);
              router.push(`/interview/${created.id}`);
            }}
          >
            Try a higher difficulty
          </Button>
          {!getBypassToken() ? (
            <Link href={`/sign-in?next=/report/${data.id}`}>
              <Button variant="primary">Save this report</Button>
            </Link>
          ) : (
            <Button
              variant="primary"
              onClick={async () => {
                await claimSession(data.id);
                setMessage("Saved to your history.");
              }}
            >
              Save to history
            </Button>
          )}
        </div>
        {message ? <p className="mt-3 text-sm">{message}</p> : null}

        <footer className="mt-12 border-t border-border pt-6 text-sm text-muted-foreground">
          {report.ethical_reminder}
        </footer>
      </main>
    </div>
  );
}

function buildMarkdown(data: Awaited<ReturnType<typeof getReport>>) {
  const r = data.report;
  return [
    `# InterviewOS report`,
    `Score: ${r.overall_score}/100`,
    r.overall_summary,
    "",
    ...Object.entries(r.rubric).map(
      ([k, v]) => `- ${k}: ${v.assessed ? `${v.score}/5` : "n/a"} — ${v.feedback}`,
    ),
  ].join("\n");
}
