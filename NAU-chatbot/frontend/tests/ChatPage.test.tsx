import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChatPage } from "../src/pages/ChatPage";
import type { ChatMessage } from "../src/types/chat";

const send = vi.fn();
const retryLast = vi.fn();
const reset = vi.fn();
const refreshConversations = vi.fn();
const loadMoreConversations = vi.fn();
const renameConversation = vi.fn();
const removeConversation = vi.fn();
const logout = vi.fn();
const { transcribeAudio } = vi.hoisted(() => ({ transcribeAudio: vi.fn() }));

vi.mock("../src/api/speech", () => ({
  speechApi: { transcribeAudio },
}));

class FakeMediaRecorder {
  static instances: FakeMediaRecorder[] = [];
  static isTypeSupported = vi.fn(() => true);

  readonly mimeType: string;
  readonly stream: MediaStream;
  state: RecordingState = "inactive";
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  onstop: (() => void) | null = null;

  constructor(stream: MediaStream, options?: MediaRecorderOptions) {
    this.stream = stream;
    this.mimeType = options?.mimeType ?? "audio/webm";
    FakeMediaRecorder.instances.push(this);
  }

  start() {
    this.state = "recording";
  }

  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["browser-audio"], { type: this.mimeType }) } as BlobEvent);
    this.onstop?.();
  }
}

const stopTrack = vi.fn();
const mediaStream = {
  getTracks: () => [{ stop: stopTrack }],
} as unknown as MediaStream;
const getUserMedia = vi.fn();

type ChatStatus = "connecting" | "ready" | "sending" | "error";

let chatState: {
  messages: ChatMessage[];
  status: ChatStatus;
  error: string | null;
  isBusy: boolean;
} = {
  messages: [],
  status: "ready",
  error: null,
  isBusy: false,
};

vi.mock("../src/features/chat/useChat", () => ({
  useChat: () => ({
    ...chatState,
    send,
    retryLast,
    reset,
    reconnect: vi.fn(),
  }),
}));

vi.mock("../src/features/chat/useConversations", () => ({
  useConversations: () => ({
    items: [],
    total: 0,
    error: null,
    loading: false,
    refresh: refreshConversations,
    loadMore: loadMoreConversations,
    rename: renameConversation,
    remove: removeConversation,
  }),
}));

vi.mock("../src/features/auth/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "user-1", name: "Test User", email: "test@iit.tn", role: "USER" },
    logout,
  }),
}));

const userMessage: ChatMessage = {
  id: "user-1",
  role: "user",
  content: "Je cherche une formation.",
  createdAt: "2026-09-01T09:00:00Z",
  delivery: "sent",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <ChatPage />
    </MemoryRouter>,
  );
}

describe("ChatPage", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "onLine", { configurable: true, value: true });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia },
    });
    Object.defineProperty(globalThis, "MediaRecorder", {
      configurable: true,
      value: FakeMediaRecorder,
    });
    chatState = { messages: [], status: "ready", error: null, isBusy: false };
    FakeMediaRecorder.instances = [];
    send.mockClear();
    retryLast.mockClear();
    reset.mockClear();
    refreshConversations.mockClear();
    loadMoreConversations.mockClear();
    renameConversation.mockClear();
    removeConversation.mockClear();
    logout.mockClear();
    transcribeAudio.mockReset();
    getUserMedia.mockReset();
    stopTrack.mockClear();
    getUserMedia.mockResolvedValue(mediaStream);
    transcribeAudio.mockResolvedValue({ text: "ena nheb na3ref les formations" });
    reset.mockResolvedValue(undefined);
  });

  it("renders a focused welcome state", () => {
    renderPage();

    expect(screen.getByText("Institut International")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Comment puis-je vous aider/ })).toBeInTheDocument();
    expect(screen.getByLabelText("Questions suggérées")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Posez votre question…")).toBeInTheDocument();
  });

  it("offers keyboard-accessible suggested questions", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: "Quelles formations propose l’IIT ?" }));
    expect(send).toHaveBeenCalledWith("Quelles formations propose l’IIT ?");
  });

  it("sends typed text without rendering it as HTML", async () => {
    const user = userEvent.setup();
    renderPage();

    const input = screen.getByLabelText("Votre message");
    await user.type(input, "Bonjour <script>alert(1)</script>");
    await user.click(screen.getByRole("button", { name: "Envoyer le message" }));

    expect(send).toHaveBeenCalledWith("Bonjour <script>alert(1)</script>");
    expect(screen.queryByText("alert(1)", { selector: "script" })).not.toBeInTheDocument();
  });

  it("keeps multiline input behavior", async () => {
    const user = userEvent.setup();
    renderPage();

    const input = screen.getByLabelText("Votre message");
    await user.type(input, "Première ligne{shift>}{enter}{/shift}Deuxième ligne");
    expect(input).toHaveValue("Première ligne\nDeuxième ligne");
    expect(send).not.toHaveBeenCalled();
  });

  it("renders a subtle loading state while preserving the conversation", () => {
    chatState = { messages: [userMessage], status: "sending", error: null, isBusy: true };
    renderPage();

    expect(screen.getByText("Je cherche une formation.")).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "L’assistant prépare sa réponse" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Envoyer le message" })).toBeDisabled();
  });

  it("shows a safe error and keeps retry available", async () => {
    const user = userEvent.setup();
    chatState = {
      messages: [{ ...userMessage, delivery: "failed" }],
      status: "error",
      error: "Internal server error: database unavailable",
      isBusy: false,
    };
    renderPage();

    expect(screen.getByRole("alert")).toHaveTextContent("Impossible d’obtenir une réponse.");
    expect(screen.queryByText(/database unavailable/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Réessayer/ }));
    expect(retryLast).toHaveBeenCalledOnce();
  });

  it("starts a new conversation from the single sidebar action", async () => {
    const user = userEvent.setup();
    chatState = { messages: [userMessage], status: "ready", error: null, isBusy: false };
    renderPage();

    await user.click(screen.getByRole("button", { name: "Nouvelle conversation" }));

    await waitFor(() => expect(reset).toHaveBeenCalledOnce());
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("disables sending while connecting", () => {
    chatState = { messages: [], status: "connecting", error: null, isBusy: true };
    renderPage();

    expect(screen.getByLabelText("Votre message")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Envoyer le message" })).toBeDisabled();
  });

  it("shows the offline state and prevents message submission", async () => {
    const user = userEvent.setup();
    Object.defineProperty(navigator, "onLine", { configurable: true, value: false });
    renderPage();

    expect(screen.getByRole("status")).toHaveTextContent("Connexion interrompue");
    const input = screen.getByLabelText("Votre message");
    await user.type(input, "Bonjour");
    expect(screen.getByRole("button", { name: "Envoyer le message" })).toBeDisabled();
    expect(send).not.toHaveBeenCalled();
  });

  it("formats long assistant answers as safe lists and links", () => {
    chatState = {
      messages: [
        {
          id: "assistant-1",
          role: "assistant",
          content: "### Détails\n\n- Première option\n- Plus d’informations : https://iit.tn/admission",
          createdAt: "2026-09-01T09:01:00Z",
          delivery: "sent",
        },
      ],
      status: "ready",
      error: null,
      isBusy: false,
    };
    renderPage();

    expect(screen.getByRole("heading", { name: "Détails" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByRole("link", { name: "https://iit.tn/admission" })).toHaveAttribute(
      "rel",
      "noreferrer",
    );
  });

  it("records on first click and transcribes on second click", async () => {
    const user = userEvent.setup();
    renderPage();

    const microphone = screen.getByRole("button", { name: "Démarrer l’enregistrement vocal" });
    await user.click(microphone);

    expect(getUserMedia).toHaveBeenCalledWith({ audio: true });
    expect(screen.getByRole("button", { name: "Arrêter l’enregistrement vocal" })).toBeInTheDocument();
    expect(screen.getByText(/Enregistrement en cours/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Arrêter l’enregistrement vocal" }));

    await waitFor(() => expect(transcribeAudio).toHaveBeenCalledWith(expect.any(Blob)));
    await waitFor(() => expect(screen.getByLabelText("Votre message")).toHaveValue("ena nheb na3ref les formations"));
    expect(stopTrack).toHaveBeenCalled();
    expect(send).not.toHaveBeenCalled();
  });

  it("preserves existing text when adding a transcription", async () => {
    const user = userEvent.setup();
    renderPage();
    const input = screen.getByLabelText("Votre message");
    await user.type(input, "Bonjour");

    await user.click(screen.getByRole("button", { name: "Démarrer l’enregistrement vocal" }));
    await user.click(screen.getByRole("button", { name: "Arrêter l’enregistrement vocal" }));

    await waitFor(() => expect(input).toHaveValue("Bonjour ena nheb na3ref les formations"));
    expect(send).not.toHaveBeenCalled();
  });

  it("shows a safe microphone permission error", async () => {
    const user = userEvent.setup();
    getUserMedia.mockRejectedValueOnce(new DOMException("denied", "NotAllowedError"));
    renderPage();

    await user.click(screen.getByRole("button", { name: "Démarrer l’enregistrement vocal" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Impossible d’accéder au microphone.");
    expect(transcribeAudio).not.toHaveBeenCalled();
  });

  it("shows a safe transcription error", async () => {
    const user = userEvent.setup();
    transcribeAudio.mockRejectedValueOnce(new Error("backend details"));
    renderPage();

    await user.click(screen.getByRole("button", { name: "Démarrer l’enregistrement vocal" }));
    await user.click(screen.getByRole("button", { name: "Arrêter l’enregistrement vocal" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("La transcription audio a échoué. Réessayez.");
    expect(screen.queryByText("backend details")).not.toBeInTheDocument();
  });

  it("disables microphone while transcription is pending", async () => {
    const user = userEvent.setup();
    let finishTranscription: ((value: { text: string }) => void) | undefined;
    transcribeAudio.mockReturnValueOnce(new Promise((resolve) => {
      finishTranscription = resolve;
    }));
    renderPage();

    await user.click(screen.getByRole("button", { name: "Démarrer l’enregistrement vocal" }));
    await user.click(screen.getByRole("button", { name: "Arrêter l’enregistrement vocal" }));

    const microphone = screen.getByRole("button", { name: "Démarrer l’enregistrement vocal" });
    await waitFor(() => expect(microphone).toBeDisabled());
    expect(screen.getByText("Transcription en cours…")).toBeInTheDocument();

    finishTranscription?.({ text: "texte final" });
    await waitFor(() => expect(microphone).toBeEnabled());
  });

  it("keeps the existing manual send flow after transcription", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: "Démarrer l’enregistrement vocal" }));
    await user.click(screen.getByRole("button", { name: "Arrêter l’enregistrement vocal" }));
    await waitFor(() => expect(screen.getByLabelText("Votre message")).toHaveValue("ena nheb na3ref les formations"));
    expect(send).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Envoyer le message" }));
    expect(send).toHaveBeenCalledWith("ena nheb na3ref les formations");
  });
});
