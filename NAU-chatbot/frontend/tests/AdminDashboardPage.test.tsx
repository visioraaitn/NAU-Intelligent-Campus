import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { adminApi } from "../src/api/admin";
import { AdminDashboardPage } from "../src/pages/AdminDashboardPage";
import type { AcademicResource } from "../src/types/academic";

const totals: Partial<Record<AcademicResource, number>> = {
  parcours: 4,
  formations: 10,
  specialisations: 7,
  tarifs: 12,
  "orientation-rules": 9,
  accreditations: 3,
};

describe("AdminDashboardPage", () => {
  beforeEach(() => {
    vi.spyOn(adminApi, "list").mockImplementation((resource) =>
      Promise.resolve({ items: [], total: totals[resource] ?? 0, limit: 1, offset: 0 }),
    );
    vi.spyOn(adminApi, "orientationMatrix").mockResolvedValue({
      profiles: [],
      diagnostics: [
        {
          formation_id: 1,
          formation_name: "Formation A",
          has_admission_rule: false,
          has_tariff: false,
          specialisation_count: 0,
          element_count: 0,
          issues: ["Règle manquante", "Tarif manquant"],
        },
        {
          formation_id: 2,
          formation_name: "Formation B",
          has_admission_rule: true,
          has_tariff: false,
          specialisation_count: 2,
          element_count: 4,
          issues: ["Tarif manquant"],
        },
        {
          formation_id: 3,
          formation_name: "Formation C",
          has_admission_rule: true,
          has_tariff: true,
          specialisation_count: 1,
          element_count: 3,
          issues: [],
        },
      ],
    });
  });

  it("renders existing counters and quality indicators", async () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);

    expect(await screen.findByLabelText("Cycles académiques : 4")).toBeInTheDocument();
    expect(screen.getByLabelText("Formations : 10")).toBeInTheDocument();
    expect(screen.getByLabelText("Spécialisations : 7")).toBeInTheDocument();
    expect(await screen.findByLabelText("À vérifier : 2")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /1 formation sans règle d’admission/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /2 formations sans tarif/ })).toBeInTheDocument();
  });

  it("preserves workflow, resource and public assistant navigation", async () => {
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);

    expect(screen.getByRole("link", { name: /Catalogue académique Gérer/ })).toHaveAttribute("href", "/admin/catalogue");
    expect(screen.getByRole("link", { name: /Admission et inscription/ })).toHaveAttribute("href", "/admin/admission");
    expect(screen.getByRole("link", { name: /Diagnostic d’orientation/ })).toHaveAttribute("href", "/admin/orientation-matrix");
    expect(screen.getByRole("link", { name: /Voir l’assistant public/ })).toHaveAttribute("href", "/");
    expect(await screen.findByRole("link", { name: /Tarifs 12/ })).toHaveAttribute("href", "/admin/tarifs");
  });

  it("keeps counters usable if the diagnostic API is unavailable", async () => {
    vi.mocked(adminApi.orientationMatrix).mockRejectedValue(new Error("Unavailable"));
    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);

    expect(await screen.findByText("Le diagnostic est momentanément indisponible.")).toBeInTheDocument();
    expect(screen.getByLabelText("À vérifier : indisponible")).toBeInTheDocument();
    expect(await screen.findByLabelText("Formations : 10")).toBeInTheDocument();
  });
});
