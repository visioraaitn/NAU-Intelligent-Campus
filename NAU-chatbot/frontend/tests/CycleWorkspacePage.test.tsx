import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { adminApi } from "../src/api/admin";
import { CycleCataloguePage } from "../src/pages/CycleCataloguePage";
import { CycleWorkspacePage } from "../src/pages/CycleWorkspacePage";
import type { AcademicCycleOverviewResponse, AcademicEntity } from "../src/types/academic";

const base = { actif: true, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" };
const cycle = { ...base, id: 3, code: "CYCLE_TEST", nom: "Cycle Test", duree_annees: 3, description: "Description du cycle" };
const formation = { ...base, id: 30, parcours_id: 3, code: "FORMATION_TEST", nom: "Formation Test", intitule_diplome: "Diplôme Test", duree_annees: 3, nb_semestres: 6, credits_total: 180, langues_enseignement: ["FRANCAIS"], description: null, source_ref: null };
const link = { ...base, id: 90, parcours_id: null, formation_id: null, specialisation_id: null, parent_id: null, type_element: "LIEN_PREINSCRIPTION" as const, code: "PREINSCRIPTION_URL", nom: "Préinscription", description: null, valeur: "https://example.test/inscription", organisme: null, ordre_affichage: 1, source_ref: "SOURCE", };
const overview: AcademicCycleOverviewResponse = { parcours: cycle, formations: [formation], effective_elements: [{ element: link, scope: "GLOBAL" }], tarifs: [] };

function page(items: AcademicEntity[]) {
  return Promise.resolve({ items, total: items.length, limit: 100, offset: 0 });
}

function Location() {
  const location = useLocation();
  return <output aria-label="URL courante">{location.pathname}{location.search}</output>;
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(adminApi, "cycleOverview").mockResolvedValue(overview);
  vi.spyOn(adminApi, "list").mockImplementation((resource) => {
    if (resource === "parcours") return page([cycle]);
    if (resource === "formations") return page([formation]);
    return page([]);
  });
});

describe("Cycle admin workflow", () => {
  it("opens a Cycle Workspace from the academic catalogue", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter initialEntries={["/admin/catalogue"]}><Routes><Route path="/admin/catalogue" element={<CycleCataloguePage />} /><Route path="/admin/cycle-workspace" element={<Location />} /></Routes></MemoryRouter>);

    await user.click(await screen.findByRole("link", { name: /Cycle Test/ }));

    expect(screen.getByLabelText("URL courante")).toHaveTextContent("/admin/cycle-workspace?parcours_id=3");
  });

  it("persists wizard step one before showing formations", async () => {
    const user = userEvent.setup();
    const create = vi.spyOn(adminApi, "create").mockResolvedValue({ entity: cycle, action: "CREATED", indexing_status: "NOT_APPLICABLE", event_ids: [] });
    render(<MemoryRouter><CycleCataloguePage /></MemoryRouter>);

    await user.click(await screen.findByRole("button", { name: "Nouveau cycle académique" }));
    const dialog = screen.getByRole("dialog", { name: "Nouveau cycle académique" });
    await user.type(within(dialog).getByLabelText(/^Code/), "NEW_CYCLE");
    await user.type(within(dialog).getByLabelText(/^Nom/), "Nouveau cycle");
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer et continuer" }));

    await waitFor(() => expect(create).toHaveBeenCalledWith("parcours", expect.objectContaining({ code: "NEW_CYCLE", nom: "Nouveau cycle" })));
    expect((await within(dialog).findAllByRole("heading", { name: "Formations du cycle" })).length).toBeGreaterThan(0);
  });

  it("edits the general cycle information", async () => {
    const user = userEvent.setup();
    const update = vi.spyOn(adminApi, "update").mockResolvedValue({ entity: cycle, action: "UPDATED", indexing_status: "NOT_APPLICABLE", event_ids: [] });
    render(<MemoryRouter initialEntries={["/admin/cycle-workspace?parcours_id=3"]}><CycleWorkspacePage /></MemoryRouter>);

    await user.click(await screen.findByRole("button", { name: "Modifier" }));
    const dialog = screen.getByRole("dialog", { name: "Modifier le cycle académique" });
    const name = within(dialog).getByLabelText(/^Nom/);
    await user.clear(name);
    await user.type(name, "Cycle modifié");
    await user.click(within(dialog).getByRole("button", { name: "Enregistrer" }));

    await waitFor(() => expect(update).toHaveBeenCalledWith("parcours", 3, expect.objectContaining({ nom: "Cycle modifié" })));
  });

  it("adds a formation with the cycle fixed automatically", async () => {
    const user = userEvent.setup();
    const create = vi.spyOn(adminApi, "create").mockResolvedValue({ entity: formation, action: "CREATED", indexing_status: "NOT_APPLICABLE", event_ids: [] });
    render(<MemoryRouter initialEntries={["/admin/cycle-workspace?parcours_id=3&section=formations"]}><CycleWorkspacePage /></MemoryRouter>);

    await user.click(await screen.findByRole("button", { name: "Ajouter une formation" }));
    const dialog = screen.getByRole("dialog", { name: "Ajouter une formation" });
    expect(within(dialog).queryByLabelText(/Cycle académique/)).not.toBeInTheDocument();
    await user.type(within(dialog).getByLabelText(/^Code/), "FORMATION_NEW");
    await user.type(within(dialog).getByRole("textbox", { name: /^Nom/ }), "Formation nouvelle");
    await user.click(within(dialog).getByRole("button", { name: /Créer/ }));

    await waitFor(() => expect(create).toHaveBeenCalledWith("formations", expect.objectContaining({ parcours_id: 3, code: "FORMATION_NEW" })));
  });

  it("creates a cycle override when editing inherited pre-registration", async () => {
    const user = userEvent.setup();
    const create = vi.spyOn(adminApi, "create").mockResolvedValue({ entity: link, action: "CREATED", indexing_status: "NOT_APPLICABLE", event_ids: [] });
    render(<MemoryRouter initialEntries={["/admin/cycle-workspace?parcours_id=3&section=inscription"]}><CycleWorkspacePage /></MemoryRouter>);

    await user.click(await screen.findByRole("button", { name: "Modifier" }));
    const dialog = screen.getByRole("dialog", { name: "Adapter pour ce cycle" });
    const value = within(dialog).getByLabelText(/Valeur ou lien/);
    await user.clear(value);
    await user.type(value, "https://cycle.example.test");
    await user.click(within(dialog).getByRole("button", { name: /Créer/ }));

    await waitFor(() => expect(create).toHaveBeenCalledWith("elements", expect.objectContaining({ parcours_id: 3, code: "PREINSCRIPTION_URL", valeur: "https://cycle.example.test" })));
  });
});
