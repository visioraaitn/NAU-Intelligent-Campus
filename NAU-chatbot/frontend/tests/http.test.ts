import { afterEach, describe, expect, it, vi } from "vitest";
import { apiRequest, ApiError, setAccessToken } from "../src/api/http";

describe("apiRequest", () => {
  afterEach(() => setAccessToken(null));

  it("adds the in-memory bearer token and includes cookies", async () => {
    setAccessToken("memory-only-token");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await apiRequest<{ ok: boolean }>("/admin/parcours");

    const options = fetchMock.mock.calls[0]?.[1];
    expect(new Headers(options?.headers).get("Authorization")).toBe("Bearer memory-only-token");
    expect(options?.credentials).toBe("include");
  });

  it("maps server failures to safe API errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "CONFLICT", message: "Cette entrée est utilisée." } }), {
        status: 409,
      }),
    );

    await expect(apiRequest("/admin/parcours/1", { method: "DELETE" })).rejects.toEqual(
      expect.objectContaining<Partial<ApiError>>({ status: 409, code: "CONFLICT", message: "Cette entrée est utilisée." }),
    );
  });
});
