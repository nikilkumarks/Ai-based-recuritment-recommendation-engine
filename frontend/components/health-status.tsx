"use client";

import { useEffect, useState } from "react";
import { getApiBaseUrl, getHealth } from "@/lib/api";

type Status = "loading" | "ok" | "error";

export function HealthStatus() {
  const [status, setStatus] = useState<Status>("loading");
  const [detail, setDetail] = useState("Checking API…");

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((data) => {
        if (cancelled) return;
        setStatus("ok");
        setDetail(`${data.service} reported ${data.status} at ${getApiBaseUrl()}`);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setStatus("error");
        const message = error instanceof Error ? error.message : "Unknown error";
        setDetail(`${message}. Tried ${getApiBaseUrl()}/api/v1/health`);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const tone =
    status === "ok" ? "text-[var(--success)]" : status === "error" ? "text-[var(--danger)]" : "text-[var(--muted)]";

  return (
    <p className={`font-mono text-sm ${tone}`} data-testid="api-health">
      {detail}
    </p>
  );
}
