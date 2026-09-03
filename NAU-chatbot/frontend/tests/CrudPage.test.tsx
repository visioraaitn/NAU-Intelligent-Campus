import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { adminApi, type AdminListParams } from "../src/api/admin";
import { CrudPage } from "../src/features/admin/CrudPage";
import { entityConfigs } from "../src/features/admin/entityConfig";
import type { AcademicEntity, AcademicResource } from "../src/types/academic";

const cycleIngenieur: AcademicEntity = {
  id: 3,
  code: "INGENIEUR",
  nom: "Cycle Ingénieur",
  duree_annees: 3,
  actif: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const licence: AcademicEntity = {
  ...cycleIngenieur,
  id: 2,
  code: "LICENCE",
  nom: "Licence",
};

const genieInfo: AcademicEntity = {
  ...cycleIngenieur,
  id: 30,
  parcours_id: 3,
  code: "INGENIEUR_INFO",
  nom: "Génie Informatique",
  intitule_diplome: "Diplôme national d’ingénieur",
  langues_enseignement: ["FRANCAIS"],
};

const licenceInfo: AcademicEntity = {
  ...genieInfo,
  id: 20,
  parcours_id: 2,
  code: "LICENCE_INFO",
  nom: "Licence Informatique",
};

const sdia: AcademicEntity = {
  ...cycleIngenieur,
  id: 301,
  formation_id: 30,
  code: "SDIA",
  nom: "Science des Données et Intelligence Artificielle",
};

const web: AcademicEntity = {
  ...cycleIngenieur,
  id: 201,
  formation_id: 20,
  code: "WEB",
  nom: "Développement Web",
};

const parcours = [licence, cycleIngenieur];
const formations = [licenceInfo, genieInfo];
const specialisations = [web, sdia];

function page(items: AcademicEntity[]) {
  return Promise.resolve({ items, total: items.length, limit: 20, offset: 0 });
}

function mockLists(options: { emptySpecialisations?: boolean } = {}) {
  return vi.spyOn(adminApi, "list").mockImplementation(
    (resource: AcademicResource, params: AdminListParams = {}) => {
      if (resource === "parcours") return page(parcours);
      if (resource === "formations") {
        return page(params.parcoursId
          ? formations.filter((item) => Number(item.parcours_id) === params.parcoursId)
          : formations);
      }
      if (resource === "specialisations") {
        if (options.emptySpecialisations) return page([]);
        return page(specialisations.filter(
          (item) => !params.formationId || Number(item.formation_id) === params.formationId,
        ));
      }
      return page([]);
    },
  );
}

function CurrentLocation() {
  const location = useLocation();
  return <output aria-label="URL courante">{location.pathname}{location.search}</output>;
}

describe("CrudPage hierarchical navigation", () => {
  it("opens formations with the selected parcours id in the URL", async () => {
    mockLists();
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/admin/parcours"]}>
        <Routes>
          <Route path="/admin/parcours" element={<CrudPage config={entityConfigs.parcours} />} />
          <Route path="/admin/cycle-workspace" element={<CurrentLocation />} />
        </Routes>
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("link", { name: "Ouvrir Cycle Ingénieur" }));
    expect(screen.getByLabelText("URL courante")).toHaveTextContent(
      "/admin/cycle-workspace?parcours_id=3",
    );
  });

  it("opens the requested formation workspace", async () => {
    mockLists();
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/admin/formations?parcours_id=3"]}>
        <Routes>
          <Route path="/admin/formations" element={<CrudPage config={entityConfigs.formations} />} />
          <Route path="/admin/academic-overview" element={<CurrentLocation />} />
        </Routes>
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("link", { name: "Ouvrir Génie Informatique" }));
    expect(screen.getByLabelText("URL courante")).toHaveTextContent(
      "/admin/academic-overview?formation_id=30",
    );
  });

  it.each([
    ["30", "Science des Données et Intelligence Artificielle", "Développement Web"],
    ["20", "Développement Web", "Science des Données et Intelligence Artificielle"],
  ])("restores formation %s from the URL and filters its specialisations", async (
    formationId,
    expectedName,
    excludedName,
  ) => {
    const list = mockLists();

    render(
      <MemoryRouter initialEntries={[`/admin/specialisations?formation_id=${formationId}`]}>
        <CrudPage config={entityConfigs.specialisations} />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("combobox", { name: "Filtrer par formation" })).toHaveValue(formationId);
    expect(await screen.findByText(expectedName)).toBeInTheDocument();
    expect(screen.queryByText(excludedName)).not.toBeInTheDocument();
    await waitFor(() => {
      expect(list).toHaveBeenCalledWith(
        "specialisations",
        expect.objectContaining({ formationId: Number(formationId) }),
      );
    });
  });

  it("keeps formation actions independent from row navigation", async () => {
    mockLists();
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/admin/formations?parcours_id=3"]}>
        <Routes>
          <Route path="/admin/formations" element={<><CurrentLocation /><CrudPage config={entityConfigs.formations} /></>} />
        </Routes>
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("button", { name: "Modifier Génie Informatique" }));
    expect(screen.getByLabelText("URL courante")).toHaveTextContent("/admin/formations?parcours_id=3");
    await user.click(screen.getByRole("button", { name: "Fermer" }));

    await user.click(screen.getByRole("button", { name: "Supprimer Génie Informatique" }));
    expect(screen.getByRole("dialog", { name: "Supprimer définitivement" })).toBeInTheDocument();
    expect(screen.getByLabelText("URL courante")).toHaveTextContent("/admin/formations?parcours_id=3");
  });

  it("shows the dynamic breadcrumb and preserves the parcours return filter", async () => {
    mockLists();

    render(
      <MemoryRouter initialEntries={["/admin/specialisations?formation_id=30&parcours_id=3"]}>
        <CrudPage config={entityConfigs.specialisations} />
      </MemoryRouter>,
    );

    const breadcrumb = await screen.findByRole("navigation", { name: "Fil d’Ariane" });
    expect(within(breadcrumb).getByRole("link", { name: "Cycle Ingénieur" })).toHaveAttribute(
      "href",
      "/admin/formations?parcours_id=3",
    );
    expect(within(breadcrumb).getByRole("link", { name: "Génie Informatique" })).toHaveAttribute(
      "href",
      "/admin/specialisations?formation_id=30&parcours_id=3",
    );
    expect(within(breadcrumb).getByText("Spécialisations")).toHaveAttribute("aria-current", "page");
  });

  it("updates formation and parcours query params when changing context", async () => {
    mockLists();
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/admin/specialisations?formation_id=30&parcours_id=3"]}>
        <Routes>
          <Route path="/admin/specialisations" element={<><CurrentLocation /><CrudPage config={entityConfigs.specialisations} /></>} />
        </Routes>
      </MemoryRouter>,
    );

    await user.selectOptions(
      await screen.findByRole("combobox", { name: "Filtrer par formation" }),
      "20",
    );

    expect(screen.getByLabelText("URL courante")).toHaveTextContent(
      "/admin/specialisations?formation_id=20&parcours_id=2",
    );
    expect(await screen.findByText("Développement Web")).toBeInTheDocument();
  });

  it("shows a contextual empty state and preselects formation when adding", async () => {
    mockLists({ emptySpecialisations: true });
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/admin/specialisations?formation_id=30&parcours_id=3"]}>
        <CrudPage config={entityConfigs.specialisations} />
      </MemoryRouter>,
    );

    expect(await screen.findByText(
      "Aucune spécialisation n’est encore définie pour cette formation.",
    )).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^Ajouter$/ }));

    let dialog = screen.getByRole("dialog", { name: "Nouvelle spécialisation" });
    expect(within(dialog).getByLabelText(/^Formation/)).toHaveValue("30");
    await user.click(within(dialog).getByRole("button", { name: "Fermer" }));

    await user.click(screen.getByRole("button", { name: "Ajouter une spécialisation" }));

    dialog = screen.getByRole("dialog", { name: "Nouvelle spécialisation" });
    expect(within(dialog).getByLabelText(/^Formation/)).toHaveValue("30");
  });
});
