import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AdminLayout } from "../src/layouts/AdminLayout";

vi.mock("../src/features/auth/AuthContext", () => ({
  useAuth: () => ({ logout: vi.fn() }),
}));

describe("Admin navigation", () => {
  it("keeps business navigation simple and raw CRUD available", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter initialEntries={["/admin"]}><Routes><Route path="/admin" element={<AdminLayout />}><Route index element={<div>Contenu</div>} /></Route></Routes></MemoryRouter>);

    expect(screen.getByRole("link", { name: /Catalogue académique/ })).toHaveAttribute("href", "/admin/catalogue");
    expect(screen.getByRole("link", { name: /Admission & inscription/ })).toHaveAttribute("href", "/admin/admission");
    expect(screen.getAllByRole("link", { name: /^Tarifs/ })[0]).toHaveAttribute("href", "/admin/tarifs");
    expect(screen.getByRole("link", { name: /Ouvrir le chatbot/ })).toHaveAttribute("href", "/chat");
    await user.click(screen.getByText("Administration avancée"));
    expect(screen.getByRole("link", { name: /Formations brutes/ })).toHaveAttribute("href", "/admin/formations");
    expect(screen.getByRole("link", { name: /Éléments de formation/ })).toHaveAttribute("href", "/admin/elements");
    expect(screen.getByRole("link", { name: /Règles brutes/ })).toHaveAttribute("href", "/admin/orientation-rules");
  });
});
