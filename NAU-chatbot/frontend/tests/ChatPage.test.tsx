import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChatPage } from "../src/pages/ChatPage";

const send = vi.fn();
const retryLast = vi.fn();
const reset = vi.fn();

vi.mock("../src/features/chat/useChat", () => ({
  useChat: () => ({
    messages: [],
    status: "ready",
    error: null,
    isBusy: false,
    send,
    retryLast,
    reset,
    reconnect: vi.fn(),
  }),
}));

describe("ChatPage", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "onLine", { configurable: true, value: true });
  });

  it("sends typed text without rendering it as HTML", async () => {
    const user = userEvent.setup();
    render(<ChatPage />);

    const input = screen.getByLabelText("Votre message");
    await user.type(input, "Bonjour <script>alert(1)</script>");
    await user.click(screen.getByRole("button", { name: "Envoyer le message" }));

    expect(send).toHaveBeenCalledWith("Bonjour <script>alert(1)</script>");
    expect(screen.queryByText("alert(1)", { selector: "script" })).not.toBeInTheDocument();
  });

  it("offers keyboard-accessible suggested questions", async () => {
    const user = userEvent.setup();
    render(<ChatPage />);
    await user.click(screen.getByRole("button", { name: "Quelles formations propose l’IIT ?" }));
    expect(send).toHaveBeenCalledWith("Quelles formations propose l’IIT ?");
  });
});
