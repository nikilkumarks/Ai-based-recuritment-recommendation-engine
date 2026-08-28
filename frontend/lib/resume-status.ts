export const PARSE_STATUS_LABELS: Record<string, string> = {
  queued: "Queued",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
  needs_ocr: "Needs OCR",
};

export function parseStatusLabel(status: string): string {
  return PARSE_STATUS_LABELS[status] ?? status;
}

export function isTerminalParseStatus(status: string): boolean {
  return status === "ready" || status === "failed" || status === "needs_ocr";
}

export function formatBytes(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  return `${(size / 1024).toFixed(1)} KB`;
}
