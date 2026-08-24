import { QUALITATIVE_KEYS, type Feedback } from "@/lib/types";

export function RubricBars({ report }: { report: Feedback }) {
  return (
    <div className="space-y-3">
      {QUALITATIVE_KEYS.map(([key, label]) => {
        const item = report.rubric[key];
        const pct = item?.assessed && item.score ? (item.score / 5) * 100 : 0;
        return (
          <div key={key}>
            <div className="flex justify-between text-sm">
              <span>{label}</span>
              <span>
                {item?.assessed && item.score != null ? `${item.score}/5` : "Not assessed"}
              </span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-muted">
              <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{item?.feedback}</p>
          </div>
        );
      })}
    </div>
  );
}

export function RubricTable({ report }: { report: Feedback }) {
  const rows = Object.entries(report.rubric);
  return (
    <table className="mt-4 w-full text-left text-sm">
      <caption className="sr-only">Rubric scores</caption>
      <thead>
        <tr className="border-b border-border">
          <th className="py-2">Dimension</th>
          <th>Score</th>
          <th>Feedback</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([key, item]) => (
          <tr key={key} className="border-b border-border align-top">
            <td className="py-2 font-medium">{key.replaceAll("_", " ")}</td>
            <td>{item.assessed && item.score != null ? `${item.score}/5` : "n/a"}</td>
            <td className="text-muted-foreground">{item.feedback}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
