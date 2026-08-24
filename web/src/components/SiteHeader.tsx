"use client";

import Link from "next/link";
import { SignIn, SignOut, ClockCounterClockwise } from "@phosphor-icons/react";
import { clerkEnabled, clearBypassToken, getBypassToken } from "@/lib/auth";
import { useEffect, useState } from "react";

function ClerkButtons() {
  const { UserButton } = require("@clerk/nextjs") as typeof import("@clerk/nextjs");
  return <UserButton />;
}

export function SiteHeader({ dark = false }: { dark?: boolean }) {
  const [signedIn, setSignedIn] = useState(false);
  useEffect(() => {
    setSignedIn(Boolean(getBypassToken()));
  }, []);
  const shell = dark
    ? "border-white/10 bg-room text-room-fg"
    : "border-border bg-background text-foreground";
  return (
    <header className={`border-b ${shell}`}>
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="text-sm font-semibold tracking-tight">
          InterviewOS
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href="/practice" className="hover:underline">
            Practice
          </Link>
          <Link href="/history" className="inline-flex items-center gap-1 hover:underline">
            <ClockCounterClockwise size={16} aria-hidden="true" />
            History
          </Link>
          {clerkEnabled() ? (
            <ClerkButtons />
          ) : signedIn ? (
            <button
              type="button"
              className="inline-flex cursor-pointer items-center gap-1 hover:underline"
              onClick={() => {
                clearBypassToken();
                setSignedIn(false);
                window.location.href = "/";
              }}
            >
              <SignOut size={16} aria-hidden="true" />
              Sign out
            </button>
          ) : (
            <Link href="/sign-in" className="inline-flex items-center gap-1 hover:underline">
              <SignIn size={16} aria-hidden="true" />
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
