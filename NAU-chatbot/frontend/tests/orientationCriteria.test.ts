import { describe, expect, it } from "vitest";
import { parseCriteriaForForm, serializeCriteriaFromForm } from "../src/features/admin/orientationCriteria";

describe("orientation criteria editor", () => {
  it("round-trips supported criteria without losing scalar types", () => {
    const criteria = {
      diplome: { in: ["PREPA", "LICENCE"] },
      score_minimum: 12,
      entretien: true,
    };

    const parsed = parseCriteriaForForm(criteria);

    expect(serializeCriteriaFromForm(parsed.rows, parsed.advanced)).toEqual(criteria);
  });

  it("preserves unknown legacy JSON while simple criteria are edited", () => {
    const criteria = {
      diplome: "LICENCE",
      legacy: { all: [{ field: "score", gte: 12 }], metadata: { version: 2 } },
    };
    const parsed = parseCriteriaForForm(criteria);
    const rows = parsed.rows.map((row) => row.key === "diplome" ? { ...row, values: ["MASTER"] } : row);

    expect(serializeCriteriaFromForm(rows, parsed.advanced)).toEqual({
      diplome: "MASTER",
      legacy: criteria.legacy,
    });
  });
});
