import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import App from "../src/App";

vi.mock("../src/features/auth/AuthContext", () => ({
  useAuth: () => ({
    status: "authenticated",
    isAuthenticated: true,
    user: { id: null, name: "Administrateur", email: null, role: "ADMIN" },
    logout: vi.fn(),
  }),
}));

vi.mock("../src/pages/ChatPage", () => ({
  ChatPage: () => <h1>Chat administrateur accessible</h1>,
}));

describe("App routes", () => {
  it("allows an authenticated administrator to open the chatbot", () => {
    render(<MemoryRouter initialEntries={["/chat"]}><App /></MemoryRouter>);

    expect(screen.getByRole("heading", { name: "Chat administrateur accessible" })).toBeInTheDocument();
  });
});
