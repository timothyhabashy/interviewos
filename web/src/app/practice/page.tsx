"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { SiteHeader } from "@/components/SiteHeader";
import { Button, ErrorSummary, Field } from "@/components/ui";
import { createSession, fetchMeta } from "@/lib/api";

type Meta = Awaited<ReturnType<typeof fetchMeta>>;

export default function PracticePage() {
  const router = useRouter();
  const summaryRef = useRef<HTMLDivElement>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [interviewType, setInterviewType] = useState("Internship");
  const [interviewMode, setInterviewMode] = useState("Auto");
  const [difficulty, setDifficulty] = useState("Auto");
  const [questionCount, setQuestionCount] = useState("3");
  const [timer, setTimer] = useState("Off");
  const [opportunity, setOpportunity] = useState("");
  const [background, setBackground] = useState("");
  const [errors, setErrors] = useState<{ id: string; message: string }[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchMeta().then(setMeta).catch(() => setMeta(null));
  }, []);

  useEffect(() => {
    if (errors.length) summaryRef.current?.focus();
  }, [errors]);

  const applySample = (key: string) => {
    const sample = meta?.samples[key];
    if (!sample) return;
    setInterviewType(sample.interview_type);
    setInterviewMode(sample.interview_mode);
    setDifficulty(sample.difficulty);
    setQuestionCount(sample.question_count ? String(sample.question_count) : "Auto");
    setTimer(
      sample.timer_seconds === 90
        ? "90"
        : sample.timer_seconds === 60
          ? "60"
          : sample.timer_seconds
            ? String(sample.timer_seconds)
            : "Off",
    );
    setOpportunity(sample.opportunity_description);
    setBackground(sample.applicant_background);
  };

  const validate = () => {
    const next: { id: string; message: string }[] = [];
    if (!interviewType) next.push({ id: "interview_type", message: "Choose an interview type" });
    return next;
  };

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const next = validate();
    setErrors(next);
    if (next.length) {
      return;
    }
    setBusy(true);
    try {
      const count = questionCount === "Auto" ? null : Number(questionCount);
      const timerSeconds = timer === "Off" ? null : Number(timer);
      const created = await createSession({
        interview_type: interviewType,
        interview_mode: interviewMode,
        difficulty,
        question_count: count,
        timer_seconds: timerSeconds,
        opportunity_description: opportunity,
        applicant_background: background,
      });
      router.push(`/interview/${created.id}`);
    } catch (err) {
      setErrors([{ id: "interview_type", message: (err as Error).message }]);
      summaryRef.current?.focus();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <SiteHeader />
      <main className="mx-auto max-w-3xl px-4 py-10">
        <h1 className="text-3xl font-semibold">Set up your interview</h1>
        <p className="mt-2 text-muted-foreground">
          Choose the room. Marketing stays on the landing page.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          {meta
            ? Object.entries(meta.samples).map(([key, sample]) => (
                <Button
                  key={key}
                  variant="ghost"
                  onClick={() => applySample(key)}
                  data-testid={`sample-${key}`}
                >
                  {sample.label}
                </Button>
              ))
            : null}
        </div>
        <form className="mt-8 space-y-5" onSubmit={onSubmit} noValidate>
          <ErrorSummary errors={errors} summaryRef={summaryRef} />
          <Field id="interview_type" label="Interview type" error={errors.find((e) => e.id === "interview_type")?.message}>
            <select
              id="interview_type"
              className="rounded-md border border-border bg-card px-3 py-2"
              value={interviewType}
              onChange={(e) => setInterviewType(e.target.value)}
              aria-describedby={errors.find((e) => e.id === "interview_type") ? "interview_type-error" : undefined}
            >
              {(meta?.interview_types || [interviewType]).map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </Field>
          <Field id="interview_mode" label="Interview mode">
            <select
              id="interview_mode"
              className="rounded-md border border-border bg-card px-3 py-2"
              value={interviewMode}
              onChange={(e) => setInterviewMode(e.target.value)}
            >
              {(meta?.interview_modes || ["Auto"]).map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </Field>
          <Field id="difficulty" label="Difficulty">
            <select
              id="difficulty"
              className="rounded-md border border-border bg-card px-3 py-2"
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
            >
              {(meta?.difficulty_levels || ["Auto"]).map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </Field>
          <Field id="question_count" label="Number of questions">
            <select
              id="question_count"
              className="rounded-md border border-border bg-card px-3 py-2"
              value={questionCount}
              onChange={(e) => setQuestionCount(e.target.value)}
            >
              {["Auto", "3", "5", "7", "10"].map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </Field>
          <Field id="timer" label="Timer" hint="You can still submit after time expires.">
            <select
              id="timer"
              className="rounded-md border border-border bg-card px-3 py-2"
              value={timer}
              onChange={(e) => setTimer(e.target.value)}
            >
              <option value="Off">Off</option>
              <option value="30">30 seconds</option>
              <option value="60">60 seconds</option>
              <option value="90">90 seconds</option>
              <option value="120">120 seconds</option>
            </select>
          </Field>
          <Field id="opportunity" label="Opportunity description (optional)">
            <textarea
              id="opportunity"
              className="min-h-28 rounded-md border border-border bg-card px-3 py-2"
              value={opportunity}
              onChange={(e) => setOpportunity(e.target.value)}
            />
          </Field>
          <Field id="background" label="Applicant background (optional)">
            <textarea
              id="background"
              className="min-h-28 rounded-md border border-border bg-card px-3 py-2"
              value={background}
              onChange={(e) => setBackground(e.target.value)}
            />
          </Field>
          <Button type="submit" variant="accent" disabled={busy} className="w-full" data-testid="start-interview">
            {busy ? "Designing your interview…" : "Start interview"}
          </Button>
        </form>
      </main>
    </div>
  );
}
