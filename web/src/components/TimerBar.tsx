"use client";

import { Timer } from "@phosphor-icons/react";
import { useEffect, useState } from "react";

export function TimerBar({
  totalSeconds,
  startedAt,
}: {
  totalSeconds: number;
  startedAt: number;
}) {
  const [remaining, setRemaining] = useState(totalSeconds);
  useEffect(() => {
    const tick = () => {
      const elapsed = (Date.now() - startedAt) / 1000;
      setRemaining(Math.max(0, Math.ceil(totalSeconds - elapsed)));
    };
    tick();
    const id = window.setInterval(tick, 250);
    return () => window.clearInterval(id);
  }, [totalSeconds, startedAt]);
  const expired = remaining <= 0;
  const pct = Math.max(0, (remaining / totalSeconds) * 100);
  return (
    <div
      className={`flex items-center gap-3 rounded-md border px-3 py-2 text-sm ${
        expired ? "border-destructive text-destructive" : "border-white/15 text-room-fg"
      }`}
      role="status"
      aria-live="polite"
    >
      <Timer size={18} aria-hidden="true" />
      <span>
        {expired
          ? "Time is up — submit your best answer."
          : `${remaining}s remaining`}
      </span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/15">
        <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function timeExpired(totalSeconds: number | null, startedAt: number | null) {
  if (!totalSeconds || !startedAt) return false;
  return (Date.now() - startedAt) / 1000 >= totalSeconds;
}
