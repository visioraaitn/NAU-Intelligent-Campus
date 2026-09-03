import { afterEach, describe, expect, it, vi } from "vitest";
import { speechApi } from "../src/api/speech";

describe("speechApi", () => {
  afterEach(() => vi.restoreAllMocks());

  it("posts the original browser blob to the dedicated speech endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ text: "transcription" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const audio = new Blob(["browser-audio"], { type: "audio/webm;codecs=opus" });

    await expect(speechApi.transcribeAudio(audio)).resolves.toEqual({ text: "transcription" });

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, options] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/v1/speech/transcribe");
    expect(options?.method).toBe("POST");
    expect(options?.body).toBeInstanceOf(FormData);
    const uploaded = (options?.body as FormData).get("audio") as File;
    expect(uploaded.type).toBe("audio/webm;codecs=opus");
    expect(uploaded.name).toBe("recording.webm");
    expect(uploaded.size).toBe(audio.size);
  });
});
