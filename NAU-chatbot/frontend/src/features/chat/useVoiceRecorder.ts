import { useCallback, useEffect, useRef, useState } from "react";
import { speechApi } from "../../api/speech";

export type VoiceInputStatus = "idle" | "recording" | "transcribing" | "error";

const preferredMimeTypes = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
];

function recorderOptions(): MediaRecorderOptions | undefined {
  const mimeType = preferredMimeTypes.find((candidate) =>
    typeof MediaRecorder.isTypeSupported !== "function" || MediaRecorder.isTypeSupported(candidate),
  );
  return mimeType ? { mimeType } : undefined;
}

export function useVoiceRecorder(onTranscription: (text: string) => void) {
  const [status, setStatus] = useState<VoiceInputStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startingRef = useRef(false);
  const mountedRef = useRef(true);
  const discardRef = useRef(false);
  const onTranscriptionRef = useRef(onTranscription);
  onTranscriptionRef.current = onTranscription;

  const stopTracks = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const transcribeRecording = useCallback(async (recorder: MediaRecorder) => {
    stopTracks();
    recorderRef.current = null;
    if (discardRef.current || !mountedRef.current) return;

    const audio = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
    chunksRef.current = [];
    if (audio.size === 0) {
      setError("Aucun son exploitable n’a été détecté.");
      setStatus("error");
      return;
    }

    setStatus("transcribing");
    try {
      const response = await speechApi.transcribeAudio(audio);
      if (!mountedRef.current) return;
      onTranscriptionRef.current(response.text);
      setError(null);
      setStatus("idle");
    } catch {
      if (!mountedRef.current) return;
      setError("La transcription audio a échoué. Réessayez.");
      setStatus("error");
    }
  }, [stopTracks]);

  const startRecording = useCallback(async () => {
    if (startingRef.current) return;
    startingRef.current = true;
    setError(null);
    discardRef.current = false;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("L’enregistrement vocal n’est pas disponible sur ce navigateur.");
      setStatus("error");
      startingRef.current = false;
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mountedRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      const options = recorderOptions();
      const recorder = options ? new MediaRecorder(stream, options) : new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        discardRef.current = true;
        stopTracks();
        recorderRef.current = null;
        if (!mountedRef.current) return;
        setError("L’enregistrement vocal a été interrompu.");
        setStatus("error");
      };
      recorder.onstop = () => void transcribeRecording(recorder);
      recorderRef.current = recorder;
      recorder.start();
      setStatus("recording");
    } catch {
      stopTracks();
      if (!mountedRef.current) return;
      setError("Impossible d’accéder au microphone.");
      setStatus("error");
    } finally {
      startingRef.current = false;
    }
  }, [stopTracks, transcribeRecording]);

  const stopRecording = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    setStatus("transcribing");
    recorder.stop();
    stopTracks();
  }, [stopTracks]);

  const toggleRecording = useCallback(() => {
    if (status === "recording") {
      stopRecording();
      return;
    }
    if (status !== "transcribing") void startRecording();
  }, [startRecording, status, stopRecording]);

  useEffect(() => () => {
    mountedRef.current = false;
    discardRef.current = true;
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    stopTracks();
  }, [stopTracks]);

  return { status, error, toggleRecording };
}
