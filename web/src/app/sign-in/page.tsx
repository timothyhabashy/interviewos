"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SiteHeader } from "@/components/SiteHeader";
import { Button, ErrorSummary, Field } from "@/components/ui";
import { clerkEnabled, setBypassToken } from "@/lib/auth";
import { claimSession } from "@/lib/api";
import { Suspense } from "react";

function SignInForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/history";
  const summaryRef = useRef<HTMLDivElement>(null);
  const [identifier, setIdentifier] = useState("");
  const [errors, setErrors] = useState<{ id: string; message: string }[]>([]);

  useEffect(() => {
    if (errors.length) summaryRef.current?.focus();
  }, [errors]);

  if (clerkEnabled()) {
    const { SignIn } = require("@clerk/nextjs") as typeof import("@clerk/nextjs");
    return <SignIn />;
  }

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!identifier.trim()) {
      setErrors([{ id: "identifier", message: "Enter an email or username." }]);
      return;
    }
    setBypassToken(identifier.trim());
    const reportId = next.startsWith("/report/") ? next.slice("/report/".length) : null;
    if (reportId) {
      try {
        await claimSession(reportId);
      } catch {
        // Guest cookie still owns it until claim succeeds on a later visit.
      }
    }
    router.push(next);
  };

  return (
    <form className="mt-8 space-y-4" onSubmit={onSubmit} noValidate>
      <ErrorSummary errors={errors} summaryRef={summaryRef} />
      <Field id="identifier" label="Email or username" error={errors.find((e) => e.id === "identifier")?.message}>
        <input
          id="identifier"
          name="username"
          autoComplete="username"
          className="rounded-md border border-border bg-card px-3 py-2"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          onPaste={(e) => {
            const text = e.clipboardData.getData("text");
            if (text) setIdentifier(text);
          }}
        />
      </Field>
      <p className="text-sm text-muted-foreground">
        Development sign-in. Paste is allowed. Password managers are not blocked.
      </p>
      <Button type="submit" variant="primary" className="w-full">
        Continue
      </Button>
    </form>
  );
}

export default function SignInPage() {
  return (
    <div>
      <SiteHeader />
      <main className="mx-auto max-w-md px-4 py-10">
        <h1 className="text-3xl font-semibold">Sign in</h1>
        <p className="mt-2 text-muted-foreground">Save reports and compare attempts over time.</p>
        <Suspense>
          <SignInForm />
        </Suspense>
      </main>
    </div>
  );
}
