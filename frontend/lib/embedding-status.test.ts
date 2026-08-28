import { describe, expect, it } from "vitest";
import { embeddingStatusLabel } from "@/lib/embedding-status";
import type { EmbeddingStatus } from "@/lib/api";

function status(name: EmbeddingStatus["status"]): EmbeddingStatus {
  return {
    status: name,
    owner_type: "profile",
    owner_id: "00000000-0000-0000-0000-000000000001",
    chunk_type: "full",
    model_name: null,
    model_version: null,
    dimensions: null,
    embedding_text_version: null,
    content_hash: null,
    created_at: null,
    reused: false,
  };
}

describe("embedding status labels", () => {
  it("maps current/stale/incompatible/missing without hiding incompatibility", () => {
    expect(embeddingStatusLabel(null)).toBe("Missing");
    expect(embeddingStatusLabel(status("missing"))).toBe("Missing");
    expect(embeddingStatusLabel(status("current"))).toBe("Ready");
    expect(embeddingStatusLabel(status("stale"))).toBe("Stale");
    expect(embeddingStatusLabel(status("incompatible"))).toBe("Incompatible");
  });
});
