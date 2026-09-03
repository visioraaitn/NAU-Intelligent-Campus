import type { AcademicResource } from "../../types/academic";

type QueryValue = string | number | null | undefined;

export function queryValue(value: unknown): QueryValue {
  return typeof value === "string" || typeof value === "number" ? value : null;
}

export function readPositiveId(params: URLSearchParams, key: string): string {
  const parsed = Number(params.get(key));
  return Number.isInteger(parsed) && parsed > 0 ? String(parsed) : "";
}

export function updateQueryParams(
  current: URLSearchParams,
  updates: Record<string, QueryValue>,
): URLSearchParams {
  const next = new URLSearchParams(current);
  for (const [key, value] of Object.entries(updates)) {
    if (value === null || value === undefined || value === "") next.delete(key);
    else next.set(key, String(value));
  }
  return next;
}

export function adminResourceUrl(
  resource: AcademicResource | "academic-overview" | "cycle-workspace",
  params: Record<string, QueryValue> = {},
): string {
  const query = updateQueryParams(new URLSearchParams(), params).toString();
  return `/admin/${resource}${query ? `?${query}` : ""}`;
}
