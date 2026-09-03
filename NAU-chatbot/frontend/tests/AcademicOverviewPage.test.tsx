import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { adminApi } from "../src/api/admin";
import { AcademicOverviewPage } from "../src/pages/AcademicOverviewPage";
import type { AcademicEntity, AcademicFormationOverview, FormationElementType } from "../src/types/academic";

const base = {
  actif: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function element(id: number, type: FormationElementType, nom: string, specialisationId: number | null = null) {
  return {
    ...base,
    id,
    parcours_id: null,
    formation_id: 30,
    specialisation_id: specialisationId,
    parent_id: null,
    type_element: type,
    code: `${type}_${id}`,
    nom,
    description: null,
    valeur: null,
    organisme: null,
    ordre_affichage: null,
    source_ref: null,
  };
}

const overview: AcademicFormationOverview = {
  parcours: { ...base, id: 3, code: "INGENIEUR", nom: "Cycle Ingénieur", duree_annees: 3, description: null },
  formation: { ...base, id: 30, parcours_id: 3, code: "INGENIEUR_INFO", nom: "Génie Informatique", intitule_diplome: "Diplôme national d’ingénieur", duree_annees: 3, nb_semestres: 6, credits_total: 180, langues_enseignement: ["FRANCAIS"], description: null, source_ref: null },
  specialisations: [{ ...base, id: 301, formation_id: 30, code: "GLID", nom: "Génie Logiciel", description: null, ordre_affichage: 1, source_ref: null }],
  elements: [
    element(1, "MODULE", "Cloud visible", 301),
    element(2, "COURS", "Architecture visible"),
    element(3, "CONTENU_PROGRAMME", "Data visible"),
    element(4, "COMPETENCE", "Compétence métier"),
    element(5, "METIER", "Data Scientist"),
    element(6, "DOMAINE_ACTIVITE", "Industrie"),
    element(7, "INFORMATION", "Information masquée"),
  ],
  effective_elements: [
    {
      scope: "PARCOURS",
      element: {
        ...element(90, "INFORMATION", "Pièces d’inscription"),
        parcours_id: 3,
        formation_id: null,
        code: "INFO_PIECES_INSCRIPTION",
      },
    },
  ],
  tarifs: [],
  effective_tarifs: [],
  orientation_rules: [],
  accreditations: [],
  rag_documents: [],
};

function page(items: AcademicEntity[]) {
  return Promise.resolve({ items, total: items.length, limit: 100, offset: 0 });
}

function renderWorkspace(section = "general") {
  const suffix = section === "general" ? "" : `&section=${section}`;
  return render(<MemoryRouter initialEntries={[`/admin/academic-overview?formation_id=30${suffix}`]}><AcademicOverviewPage /></MemoryRouter>);
}

beforeEach(() => {
  vi.spyOn(adminApi, "academicOverview").mockResolvedValue({ formations: [overview], global_elements: [], global_rag_documents: [] });
  vi.spyOn(adminApi, "list").mockImplementation((resource) => {
    if (resource === "parcours") return page([overview.parcours]);
    if (resource === "formations") return page([overview.formation]);
    if (resource === "specialisations") return page(overview.specialisations);
    if (resource === "elements") return page(overview.elements);
    return page([]);
  });
});

describe("Formation Workspace", () => {
  it("loads only the formation requested in the URL", async () => {
    renderWorkspace();
    expect(await screen.findByRole("heading", { name: "Génie Informatique" })).toBeInTheDocument();
    expect(adminApi.academicOverview).toHaveBeenCalledWith(false, 30);
  });

  it("shows only programme element types in Programme", async () => {
    const user = userEvent.setup();
    renderWorkspace("programme");
    expect(await screen.findByText("Architecture visible")).toBeInTheDocument();
    expect(screen.getByText("Data visible")).toBeInTheDocument();
    expect(screen.queryByText("Cloud visible")).not.toBeInTheDocument();
    expect(screen.queryByText("Compétence métier")).not.toBeInTheDocument();
    expect(screen.queryByText("Information masquée")).not.toBeInTheDocument();
    await user.selectOptions(screen.getByRole("combobox", { name: "Choisir la spécialisation" }), "301");
    expect(screen.getByText("Cloud visible")).toBeInTheDocument();
    expect(screen.queryByText("Architecture visible")).not.toBeInTheDocument();
  });

  it("separates competencies, jobs and activity domains", async () => {
    renderWorkspace("outcomes");
    expect(await screen.findByRole("heading", { name: "Compétences" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Métiers" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Domaines d’activité" })).toBeInTheDocument();
    expect(screen.getByText("Compétence métier")).toBeInTheDocument();
    expect(screen.queryByText("Cloud visible")).not.toBeInTheDocument();
  });

  it("automatically submits COMPETENCE and the current formation", async () => {
    const user = userEvent.setup();
    const create = vi.spyOn(adminApi, "create").mockResolvedValue({ entity: null, action: "CREATED", indexing_status: "QUEUED", event_ids: [] });
    renderWorkspace("outcomes");
    await user.click(await screen.findByRole("button", { name: "Ajouter une compétence" }));
    const dialog = screen.getByRole("dialog", { name: "Ajouter compétence" });
    expect(within(dialog).queryByLabelText(/Type d’élément/)).not.toBeInTheDocument();
    await user.type(within(dialog).getByLabelText(/^Nom/), "Architecture Cloud");
    await user.click(within(dialog).getByRole("button", { name: /Créer/ }));
    await waitFor(() => expect(create).toHaveBeenCalledWith("elements", expect.objectContaining({ formation_id: 30, type_element: "COMPETENCE", nom: "Architecture Cloud" })));
  });

  it("automatically submits the current formation for a specialization", async () => {
    const user = userEvent.setup();
    const create = vi.spyOn(adminApi, "create").mockResolvedValue({ entity: null, action: "CREATED", indexing_status: "QUEUED", event_ids: [] });
    renderWorkspace("specialisations");
    await user.click(await screen.findByRole("button", { name: "Ajouter une spécialisation" }));
    const dialog = screen.getByRole("dialog", { name: "Ajouter une spécialisation" });
    expect(within(dialog).queryByLabelText(/^Formation/)).not.toBeInTheDocument();
    await user.type(within(dialog).getByLabelText(/^Code/), "SDIA");
    await user.type(within(dialog).getByLabelText(/^Nom/), "Science des données");
    await user.click(within(dialog).getByRole("button", { name: "Créer la spécialisation" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith("specialisations", expect.objectContaining({ formation_id: 30, code: "SDIA" })));
  });

  it("labels inherited practical information", async () => {
    renderWorkspace("practical");
    expect(await screen.findByText("Pièces d’inscription")).toBeInTheDocument();
    expect(screen.getByText("Hérité du Cycle Ingénieur")).toBeInTheDocument();
  });

  it("keeps programme configuration available with zero specialization", async () => {
    vi.mocked(adminApi.academicOverview).mockResolvedValue({
      formations: [{ ...overview, specialisations: [] }],
      global_elements: [],
      global_rag_documents: [],
    });

    renderWorkspace("programme");

    expect(await screen.findByText("Architecture visible")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Choisir la spécialisation" })).not.toBeInTheDocument();
  });
});
