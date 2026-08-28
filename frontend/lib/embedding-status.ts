import type { EmbeddingStatus } from "@/lib/api";

export function embeddingStatusLabel(status: EmbeddingStatus | null | undefined): string {
  if (!status) {
    return "Missing";
  }
  if (status.status === "current") {
    return "Ready";
  }
  if (status.status === "stale") {
    return "Stale";
  }
  if (status.status === "incompatible") {
    return "Incompatible";
  }
  return "Missing";
}
