import type { ButtonHTMLAttributes, ReactNode, RefObject } from "react";

export function Button({
  children,
  type = "button",
  variant = "primary",
  disabled,
  onClick,
  className = "",
  ...rest
}: {
  children: ReactNode;
  type?: "button" | "submit";
  variant?: "primary" | "accent" | "ghost";
  disabled?: boolean;
  onClick?: () => void;
  className?: string;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const styles = {
    primary: "bg-primary text-on-primary hover:opacity-90",
    accent: "bg-accent text-on-accent hover:opacity-90",
    ghost: "border border-border bg-card hover:bg-muted",
  }[variant];
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex cursor-pointer items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-opacity duration-200 disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}

export function Field({
  id,
  label,
  children,
  error,
  hint,
}: {
  id: string;
  label: string;
  children: ReactNode;
  error?: string;
  hint?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {children}
      {hint && !error ? (
        <p id={`${id}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function ErrorSummary({
  errors,
  summaryRef,
}: {
  errors: { id: string; message: string }[];
  summaryRef: RefObject<HTMLDivElement | null>;
}) {
  if (!errors.length) return null;
  return (
    <div
      ref={summaryRef}
      role="alert"
      tabIndex={-1}
      aria-labelledby="error-title"
      className="mb-4 rounded-md border border-destructive bg-card p-4"
      data-testid="error-summary"
    >
      <h2 id="error-title" className="text-sm font-semibold">
        There is a problem
      </h2>
      <ul className="mt-2 list-disc pl-5 text-sm">
        {errors.map((error) => (
          <li key={error.id}>
            <a href={`#${error.id}`} className="underline">
              {error.message}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
