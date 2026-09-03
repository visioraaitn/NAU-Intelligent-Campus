import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CrudTable } from "../src/features/admin/CrudTable";
import { entityConfigs } from "../src/features/admin/entityConfig";
import type { AcademicEntity } from "../src/types/academic";

const cycle: AcademicEntity = {
  id: 3,
  code: "INGENIEUR",
  nom: "Cycle Ingénieur",
  actif: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const formation: AcademicEntity = {
  ...cycle,
  id: 30,
  code: "INGENIEUR_INFO",
  nom: "Génie Informatique",
  parcours_id: 3,
};

const tariff: AcademicEntity = {
  id: 300,
  actif: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  parcours_id: null,
  formation_id: 30,
  specialisation_id: null,
  langue_enseignement: "ANGLAIS",
  annee_universitaire: "2026-2027",
  frais_inscription: null,
  mensualite: 850,
  nb_mensualites: 10,
  devise: "TND",
  statut: "CONFIRME",
};

describe("CrudTable", () => {
  it("keeps a wide tariff table readable and derives its academic cycle", () => {
    render(
      <CrudTable
        config={entityConfigs.tarifs}
        entities={[tariff]}
        loading={false}
        references={{ parcours: [cycle], formations: [formation], specialisations: [] }}
        onEdit={vi.fn()}
        onToggle={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.getByRole("table")).toHaveClass("data-table--wide");
    expect(screen.getByText("Cycle Ingénieur")).toBeInTheDocument();
    expect(screen.getByText("Génie Informatique")).toBeInTheDocument();
    expect(screen.queryByText("Cycle Ingénieur / Génie Informatique")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Modifier tarif" })).toBeInTheDocument();
  });
});
