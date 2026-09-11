import { StrictMode, type PropsWithChildren } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useVoiceRecorder } from "../src/features/chat/useVoiceRecorder";
import { speechApi } from "../src/api/speech";
import { ApiError } from "../src/api/http";

class Recorder {
  static isTypeSupported = () => true;
  mimeType = "audio/webm";
  state = "inactive";
  ondataavailable?: (event: { data: Blob }) => void;
  onstop?: () => void;
  start() { this.state = "recording"; }
  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["audio"], { type: this.mimeType }) });
    this.onstop?.();
  }
}

function setup() {
  const stop = vi.fn();
  vi.stubGlobal("MediaRecorder", Recorder);
  const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] });
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
  return { stop, getUserMedia };
}

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("voice input", () => {
  it("records, transcribes and fills the composer after StrictMode effect replay", async () => {
    const { stop } = setup();
    vi.spyOn(speechApi, "transcribeAudio").mockResolvedValue({ text: "Les frais de licence" });
    const received = vi.fn();
    const { result } = renderHook(() => useVoiceRecorder(received), {
      wrapper: ({ children }: PropsWithChildren) => <StrictMode>{children}</StrictMode>,
    });
    await act(async () => result.current.toggleRecording());
    expect(result.current.status).toBe("recording");
    await act(async () => result.current.toggleRecording());
    await waitFor(() => expect(received).toHaveBeenCalledWith("Les frais de licence"));
    expect(result.current.status).toBe("idle");
    expect(stop).toHaveBeenCalled();
  });

  it("shows service unavailability and permits another recording", async () => {
    setup();
    vi.spyOn(speechApi, "transcribeAudio").mockRejectedValue(new ApiError("Unavailable", 503));
    const { result } = renderHook(() => useVoiceRecorder(vi.fn()));
    await act(async () => result.current.toggleRecording());
    await act(async () => result.current.toggleRecording());
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.error).toContain("temporairement indisponible");
    await act(async () => result.current.toggleRecording());
    expect(result.current.status).toBe("recording");
  });
});
