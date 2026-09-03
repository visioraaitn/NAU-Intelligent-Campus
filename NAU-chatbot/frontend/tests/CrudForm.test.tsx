import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CrudForm } from "../src/features/admin/CrudForm";
import { entityConfigs } from "../src/features/admin/entityConfig";

describe("CrudForm", () => {
  it("uses HTML-compatible patterns for codes containing hyphens", () => {
    render(
      <CrudForm
        config={entityConfigs.parcours}
        entity={null}
        references={{}}
        referencesLoading={false}
        referencesError={null}
        onCancel={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByLabelText(/Code/)).toHaveAttribute("pattern", "[A-Z0-9][A-Z0-9_\\-]*");
  });

  it("serializes a new academic cycle with typed values", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <CrudForm
        config={entityConfigs.parcours}
        entity={null}
        references={{}}
        referencesLoading={false}
        referencesError={null}
        onCancel={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    await user.type(screen.getByLabelText(/Code/), "MASTER");
    await user.type(screen.getByLabelText(/^Nom/), "Cycle Master");
    await user.type(screen.getByLabelText(/Durée en années/), "2");
    await user.click(screen.getByRole("button", { name: "Créer le cycle académique" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ code: "MASTER", nom: "Cycle Master", duree_annees: 2, actif: true }),
    );
  });

  it("serializes extensible teaching languages when creating a formation", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <CrudForm
        config={entityConfigs.formations}
        entity={null}
        references={{ parcours: [{ id: 2, actif: true, created_at: "", updated_at: "", code: "LICENCE", nom: "Licence" }] }}
        referencesLoading={false}
        referencesError={null}
        onCancel={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    await user.selectOptions(screen.getByLabelText(/^Cycle académique/), "2");
    await user.type(screen.getByLabelText(/^Code/), "LICENCE_TEST");
    await user.type(screen.getByLabelText(/^Nom \*/), "Licence test");
    const languages = screen.getByLabelText(/Langues d’enseignement/);
    await user.clear(languages);
    await user.type(languages, "francais, anglais, francais");
    await user.click(screen.getByRole("button", { name: "Créer la formation" }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      langues_enseignement: ["FRANCAIS", "ANGLAIS"],
    }));
  });

  it("offers tariff languages from the selected formation", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <CrudForm
        config={entityConfigs.tarifs}
        entity={null}
        references={{
          formations: [{
            id: 2,
            actif: true,
            created_at: "",
            updated_at: "",
            code: "LICENCE_INFO",
            nom: "Licence en Informatique",
            langues_enseignement: ["FRANCAIS", "ANGLAIS"],
          }],
          specialisations: [],
        }}
        referencesLoading={false}
        referencesError={null}
        onCancel={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    await user.selectOptions(screen.getByLabelText(/^Formation/), "2");
    const language = screen.getByLabelText(/^Langue d’enseignement/);
    expect(language).toHaveTextContent("Français");
    expect(language).toHaveTextContent("Anglais");
    await user.selectOptions(language, "ANGLAIS");
    await user.click(screen.getByRole("button", { name: "Créer le tarif" }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      formation_id: 2,
      langue_enseignement: "ANGLAIS",
    }));
  });

  it("rejects a JSON array for orientation criteria", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <CrudForm
        config={entityConfigs["orientation-rules"]}
        entity={null}
        references={{ formations: [{ id: 1, actif: true, created_at: "", updated_at: "", code: "L", nom: "Licence" }] }}
        referencesLoading={false}
        referencesError={null}
        onCancel={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    await user.selectOptions(screen.getByLabelText(/^Formation/), "1");
    await user.type(screen.getByLabelText(/^Code/), "RULE_1");
    await user.type(screen.getByLabelText(/^Nom/), "Admission");
    await user.selectOptions(screen.getByLabelText(/^Type/), "ADMISSION");
    const criteria = screen.getByLabelText(/Critères/);
    await user.clear(criteria);
    await user.click(criteria);
    await user.paste("[]");
    await user.click(screen.getByRole("button", { name: /Créer/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("objet JSON valide");
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
