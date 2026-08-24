"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Microphone, SpeakerHigh } from "@phosphor-icons/react";
import { InterviewerPresence } from "@/components/InterviewerPresence";
import { SiteHeader } from "@/components/SiteHeader";
import { TimerBar, timeExpired } from "@/components/TimerBar";
import { Button, ErrorSummary, Field } from "@/components/ui";
import { getSession, streamQuestion, submitTurn, completeSession } from "@/lib/api";
import type { PublicQuestion, SessionView } from "@/lib/types";

type SpeechRec = {
  lang: string;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
};

function getRecognition(): SpeechRec | null {
  const w = window as Window & {
    SpeechRecognition?: new () => SpeechRec;
    webkitSpeechRecognition?: new () => SpeechRec;
  };
  const Ctor = w.SpeechRecognition || w.webkitSpeechRecognition;
  return Ctor ? new Ctor() : null;
}

export default function InterviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const summaryRef = useRef<HTMLDivElement>(null);
  const [session, setSession] = useState<SessionView | null>(null);
  const [question, setQuestion] = useState<PublicQuestion | null>(null);
  const [spoken, setSpoken] = useState("");
  const [answer, setAnswer] = useState("");
  const [choice, setChoice] = useState<string | null>(null);
  const [errors, setErrors] = useState<{ id: string; message: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(true);
  const [usedVoice, setUsedVoice] = useState(false);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const recRef = useRef<SpeechRec | null>(null);

  useEffect(() => {
    if (errors.length) summaryRef.current?.focus();
  }, [errors]);

  useEffect(() => {
    setVoiceSupported(Boolean(getRecognition()) || Boolean((window as Window & { __PLAYWRIGHT_SPEECH__?: boolean }).__PLAYWRIGHT_SPEECH__));
  }, []);

  useEffect(() => {
    if (!id) return;
    getSession(id).then((view) => {
      setSession(view);
      setQuestion(view.question);
      setSpoken("");
      streamQuestion(
        id,
        (chunk) => setSpoken((prev) => prev + chunk),
        (q) => {
          setQuestion(q);
          setSpoken(q.question_text);
        },
        () => setStartedAt(Date.now()),
      ).catch(() => {
        if (view.question) {
          setSpoken(view.question.question_text);
          setStartedAt(Date.now());
        }
      });
    });
  }, [id]);

  const startVoice = () => {
    const rec = getRecognition();
    if (!rec) {
      setVoiceSupported(false);
      return;
    }
    rec.lang = "en-US";
    rec.interimResults = true;
    rec.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript || "")
        .join(" ");
      setAnswer(transcript);
      setUsedVoice(true);
    };
    rec.onerror = () => setListening(false);
    recRef.current = rec;
    rec.start();
    setListening(true);
  };

  const stopVoice = () => {
    recRef.current?.stop();
    setListening(false);
  };

  const readAloud = () => {
    const text = spoken || question?.question_text;
    if (!text || !window.speechSynthesis) return;
    const utter = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utter);
  };

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const next: { id: string; message: string }[] = [];
    if (!answer.trim()) next.push({ id: "answer", message: "Write your answer before submitting." });
    if (question?.answer_format === "multiple_choice_with_explanation" && !choice) {
      next.push({ id: "choice", message: "Select one of the choices." });
    }
    setErrors(next);
    if (next.length) {
      return;
    }
    if (!id) return;
    setBusy(true);
    try {
      const expired = timeExpired(session?.plan.resolved_timer_seconds ?? null, startedAt);
      const result = await submitTurn(id, {
        written_response: answer.trim(),
        selected_choice: choice,
        time_expired: expired,
        source: usedVoice ? "voice" : "text",
      });
      setAnswer("");
      setChoice(null);
      setUsedVoice(false);
      setSpoken("");
      if (result.status === "awaiting_score" || !result.question) {
        await completeSession(id);
        router.push(`/report/${id}`);
        return;
      }
      setQuestion(result.question);
      setSession((prev) =>
        prev
          ? { ...prev, status: result.status, answered_count: result.answered_count, question: result.question }
          : prev,
      );
      streamQuestion(
        id,
        (chunk) => setSpoken((prev) => prev + chunk),
        (q) => {
          setQuestion(q);
          setSpoken(q.question_text);
        },
        () => setStartedAt(Date.now()),
      ).catch(() => {
        setSpoken(result.question?.question_text || "");
        setStartedAt(Date.now());
      });
    } catch (err) {
      setErrors([{ id: "answer", message: (err as Error).message }]);
      summaryRef.current?.focus();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-room text-room-fg">
      <SiteHeader dark />
      <main className="mx-auto flex max-w-3xl flex-col gap-8 px-4 py-10">
        <p className="text-sm text-white/70">
          {session
            ? `Question ${Math.min(session.answered_count + 1, session.plan.resolved_question_count)} of ${session.plan.resolved_question_count}`
            : "Loading interview"}
        </p>
        <InterviewerPresence />
        <section
          aria-live="polite"
          aria-busy={!spoken}
          className="rounded-xl border border-white/10 bg-white/5 p-5"
          data-testid="question-speech"
        >
          <p className="text-lg leading-relaxed">{spoken || "Interviewer is thinking…"}</p>
          {question?.interviewer_note ? (
            <p className="mt-3 text-sm italic text-white/60">Coach: {question.interviewer_note}</p>
          ) : null}
          {question?.snippet ? (
            <pre className="mt-4 overflow-x-auto rounded-md bg-black/40 p-3 text-sm">{question.snippet}</pre>
          ) : null}
          {question?.latex ? (
            <pre className="mt-3 text-sm text-white/80">{question.latex}</pre>
          ) : null}
        </section>
        {session?.plan.resolved_timer_seconds && startedAt ? (
          <TimerBar totalSeconds={session.plan.resolved_timer_seconds} startedAt={startedAt} />
        ) : null}
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <ErrorSummary errors={errors} summaryRef={summaryRef} />
          {question?.answer_format === "multiple_choice_with_explanation" ? (
            <fieldset id="choice">
              <legend className="mb-2 text-sm font-medium">Choose one</legend>
              <div className="space-y-2">
                {question.choices.map((option) => (
                  <label key={option.label} className="flex cursor-pointer items-start gap-2">
                    <input
                      type="radio"
                      name="choice"
                      value={option.label}
                      checked={choice === option.label}
                      onChange={() => setChoice(option.label)}
                    />
                    <span>
                      {option.label}. {option.text}
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          ) : null}
          <Field id="answer" label="Your answer" error={errors.find((e) => e.id === "answer")?.message}>
            <textarea
              id="answer"
              className="min-h-40 w-full rounded-md border border-white/15 bg-white/5 px-3 py-2 text-room-fg"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              aria-describedby={errors.find((e) => e.id === "answer") ? "answer-error" : undefined}
            />
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="ghost"
              className="border-white/20 text-room-fg"
              onClick={listening ? stopVoice : startVoice}
              aria-pressed={listening}
              aria-label={listening ? "Stop microphone" : "Start microphone"}
            >
              <Microphone size={18} aria-hidden="true" />
              {listening ? "Stop" : "Speak"}
            </Button>
            <Button type="button" variant="ghost" className="border-white/20 text-room-fg" onClick={readAloud}>
              <SpeakerHigh size={18} aria-hidden="true" />
              Read question
            </Button>
            {!voiceSupported ? (
              <p className="text-sm text-white/70">Voice is not available in this browser. Type instead.</p>
            ) : null}
          </div>
          <Button type="submit" variant="accent" disabled={busy} className="w-full" data-testid="submit-answer">
            {busy ? "Submitting…" : "Submit answer"}
          </Button>
        </form>
      </main>
    </div>
  );
}
