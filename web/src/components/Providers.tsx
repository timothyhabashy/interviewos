"use client";

import { ClerkProvider } from "@clerk/nextjs";
import { clerkEnabled } from "@/lib/auth";
import type { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  if (clerkEnabled()) {
    return <ClerkProvider>{children}</ClerkProvider>;
  }
  return children;
}
