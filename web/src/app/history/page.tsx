"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { SiteHeader } from "@/components/SiteHeader";
import { Button } from "@/components/ui";
import { compareReports, fetchHistory } from "@/lib/api";
import { getBypassToken } from "@/lib/auth";
import type { HistoryItem } from "@/lib/types";
import { QUALITATIVE_KEYS } from "@/lib/types";

export default function HistoryPage() {
  const router = useRouter();
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [compare, setCompare] = useState<Awaited<ReturnType<typeof compareReports>> | null>(null);

  useEffect(() => {
    if (!getBypassToken()) {
      router.replace("/sign-in?next=/history");
      return;
    }
    fetchHistory()
      .then(setItems)
      .catch((err) => setError((err as Error).message));
  }, [router]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  return (
    <div>
      <SiteHeader />
      <main className="mx-auto max-w-4xl px-4 py-10">
        <h1 className="text-3xl font-semibold">History</h1>
        {error ? <p className="mt-4 text-destructive">{error}</p> : null}
        <ul className="mt-6 space-y-3">
          {(items || []).map((item) => (
            <li key={item.id} className="flex items-center justify-between rounded-lg border border-border bg-card p-4">
              <label className="flex cursor-pointer items-center gap-3">
                <input
                  type="checkbox"
                  checked={selected.includes(item.id)}
                  onChange={() => toggle(item.id)}
                />
                <span>
                  {item.interview_type} · {item.mode} · {item.difficulty}
                  {item.overall_score != null ? ` · ${item.overall_score}/100` : ""}
                </span>
              </label>
              <Link href={`/report/${item.id}`} className="text-sm underline">
                Open
              </Link>
            </li>
          ))}
        </ul>
        {!items?.length && !error ? (
          <p className="mt-6 text-muted-foreground">No saved interviews yet. Complete a practice session and save it.</p>
        ) : null}
        <div className="mt-6">
          <Button
            variant="primary"
            disabled={selected.length !== 2}
            onClick={async () => {
              const result = await compareReports(selected[0], selected[1]);
              setCompare(result);
            }}
          >
            Compare selected
          </Button>
        </div>
        {compare ? (
          <section className="mt-10">
            <h2 className="text-xl font-semibold">Comparison</h2>
            <table className="mt-4 w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2">Dimension</th>
                  <th>Left</th>
                  <th>Right</th>
                </tr>
              </thead>
              <tbody>
                {QUALITATIVE_KEYS.map(([key, label]) => (
                  <tr key={key} className="border-b border-border">
                    <td className="py-2">{label}</td>
                    <td>{compare.left.report.rubric[key]?.score ?? "n/a"}</td>
                    <td>{compare.right.report.rubric[key]?.score ?? "n/a"}</td>
                  </tr>
                ))}
                <tr>
                  <td className="py-2 font-medium">Overall</td>
                  <td>{compare.left.report.overall_score}</td>
                  <td>{compare.right.report.overall_score}</td>
                </tr>
              </tbody>
            </table>
          </section>
        ) : null}
      </main>
    </div>
  );
}
