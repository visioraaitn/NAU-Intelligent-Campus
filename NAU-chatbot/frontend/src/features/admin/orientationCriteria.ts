export type CriterionScalar = string | number | boolean | null;

export interface CriterionFormRow {
  key: string;
  operator: "EQUALS" | "IN";
  values: CriterionScalar[];
}

export interface ParsedCriteria {
  rows: CriterionFormRow[];
  advanced: Record<string, unknown>;
}

export function parseCriteriaForForm(criteria: Record<string, unknown>): ParsedCriteria {
  const rows: CriterionFormRow[] = [];
  const advanced: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(criteria)) {
    if (isScalar(value)) {
      rows.push({ key, operator: "EQUALS", values: [value] });
      continue;
    }
    if (isPlainObject(value) && Object.keys(value).length === 1 && "in" in value) {
      const members = value.in;
      if (Array.isArray(members) && members.every(isScalar)) {
        rows.push({ key, operator: "IN", values: members });
        continue;
      }
    }
    advanced[key] = value;
  }
  return { rows, advanced };
}

export function serializeCriteriaFromForm(
  rows: CriterionFormRow[],
  advanced: Record<string, unknown>,
): Record<string, unknown> {
  const result: Record<string, unknown> = { ...advanced };
  for (const row of rows) {
    const key = row.key.trim();
    if (!key || row.values.length === 0) continue;
    result[key] = row.operator === "IN"
      ? { in: [...row.values] }
      : row.values[0];
  }
  return result;
}

export function parseCriteriaValues(value: string): CriterionScalar[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function isScalar(value: unknown): value is CriterionScalar {
  return value === null || ["string", "number", "boolean"].includes(typeof value);
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
