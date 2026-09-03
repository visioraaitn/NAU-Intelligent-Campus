import type { SpeechTranscriptionResponse } from "../types/speech";
import { apiRequest } from "./http";

function audioExtension(mimeType: string): string {
  if (mimeType.includes("ogg")) return "ogg";
  if (mimeType.includes("mp4") || mimeType.includes("m4a")) return "m4a";
  if (mimeType.includes("mpeg") || mimeType.includes("mp3")) return "mp3";
  if (mimeType.includes("wav")) return "wav";
  return "webm";
}

export const speechApi = {
  transcribeAudio(audio: Blob): Promise<SpeechTranscriptionResponse> {
    const formData = new FormData();
    const mimeType = audio.type || "audio/webm";
    formData.append("audio", audio, `recording.${audioExtension(mimeType)}`);
    return apiRequest<SpeechTranscriptionResponse>("/speech/transcribe", {
      method: "POST",
      body: formData,
      auth: false,
    });
  },
};
