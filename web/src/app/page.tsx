"use client";

import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { Button } from "@/components/ui";
import { ChatText, Exam, ShieldCheck, ChartBar, Microphone } from "@phosphor-icons/react";

export default function HomePage() {
  return (
    <div>
      <SiteHeader />
      <main>
        <section className="bg-primary text-on-primary">
          <div className="mx-auto max-w-6xl px-4 py-20">
            <p className="text-sm uppercase tracking-wide text-white/80">Interview practice</p>
            <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
              Practice high-stakes interviews when you do not have insider access.
            </h1>
            <p className="mt-4 max-w-2xl text-lg text-white/85">
              A focused mock-interview room, adaptive follow-ups, and a coaching debrief — built
              for students who have talent, but not always a network to rehearse with.
            </p>
            <div className="mt-8">
              <Link href="/practice">
                <Button variant="accent">Start practice</Button>
              </Link>
            </div>
          </div>
        </section>
        <section className="mx-auto max-w-6xl px-4 py-16">
          <h2 className="text-2xl font-semibold">What you get</h2>
          <ul className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[
              {
                icon: ChatText,
                title: "A real interviewer loop",
                body: "Questions adapt to what you just said. Vague answers get probed. Misses get a follow-up.",
              },
              {
                icon: Exam,
                title: "Behavioral and technical",
                body: "Talk through stories, then reason through problems — including snippets, not only trivia.",
              },
              {
                icon: ChartBar,
                title: "A debrief you can use",
                body: "Rubric bars, question reviews, a rewrite that keeps your facts, and drills tied to your answers.",
              },
              {
                icon: Microphone,
                title: "Type or speak",
                body: "Voice is optional. You always edit the transcript before it is scored.",
              },
              {
                icon: ShieldCheck,
                title: "Coaching, not a verdict",
                body: "No hiring prediction. No invented achievements. You stay in control.",
              },
            ].map((feature) => (
              <li key={feature.title} className="rounded-lg border border-border bg-card p-5">
                <feature.icon size={24} aria-hidden="true" />
                <h3 className="mt-3 font-semibold">{feature.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{feature.body}</p>
              </li>
            ))}
          </ul>
        </section>
        <section className="border-t border-border bg-muted/40">
          <div className="mx-auto max-w-6xl px-4 py-16">
            <blockquote className="max-w-3xl text-xl font-medium">
              “The first real interview should not be the first serious practice.”
            </blockquote>
            <p className="mt-3 text-sm text-muted-foreground">InterviewOS coaching principle</p>
            <div className="mt-8">
              <Link href="/practice">
                <Button variant="primary">Start a mock interview</Button>
              </Link>
            </div>
          </div>
        </section>
        <footer className="mx-auto max-w-6xl px-4 py-10 text-sm text-muted-foreground">
          InterviewOS is coaching, not a hiring or admissions decision. Technical explanations can
          be wrong — verify them. You remain in control.
        </footer>
      </main>
    </div>
  );
}
