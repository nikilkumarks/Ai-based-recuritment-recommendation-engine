import { describe, expect, it } from "vitest";
import { formatBytes, isTerminalParseStatus, parseStatusLabel } from "@/lib/resume-status";

describe("resume status helpers", () => {
  it("labels processing states", () => {
    expect(parseStatusLabel("queued")).toBe("Queued");
    expect(parseStatusLabel("needs_ocr")).toBe("Needs OCR");
  });

  it("treats ready/failed/needs_ocr as terminal", () => {
    expect(isTerminalParseStatus("processing")).toBe(false);
    expect(isTerminalParseStatus("ready")).toBe(true);
  });

  it("formats file sizes", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
  });
});
