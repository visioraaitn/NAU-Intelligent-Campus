import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "../src/features/auth/AuthContext";
import { authApi } from "../src/api/auth";

vi.mock("../src/api/auth", () => ({
  authApi: {
    login: vi.fn(),
    refresh: vi.fn(),
    logout: vi.fn(),
  },
}));

function StatusProbe() {
  const { status } = useAuth();
  return <span>{status}</span>;
}

describe("AuthProvider", () => {
  it("restores a session through the secure refresh-cookie endpoint", async () => {
    document.cookie = "iit_csrf=csrf-before; path=/";
    vi.mocked(authApi.refresh).mockResolvedValue({
      access_token: "short-lived-access",
      token_type: "bearer",
      expires_in: 300,
      csrf_token: "csrf-after",
    });

    render(<AuthProvider><StatusProbe /></AuthProvider>);

    await waitFor(() => expect(screen.getByText("authenticated")).toBeInTheDocument());
    expect(authApi.refresh).toHaveBeenCalledWith("csrf-before");
    expect(window.sessionStorage.getItem("access_token")).toBeNull();
  });
});
