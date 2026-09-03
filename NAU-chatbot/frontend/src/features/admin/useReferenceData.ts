import { useEffect, useMemo, useState } from "react";
import { adminApi } from "../../api/admin";
import type { AcademicEntity, AcademicResource } from "../../types/academic";
import { errorMessage } from "../../utils/errors";
import type { EntityConfig } from "./entityConfig";

export type ReferenceData = Partial<Record<AcademicResource, AcademicEntity[]>>;

export function useReferenceData(config: EntityConfig, extras: AcademicResource[] = []) {
  const resources = useMemo(() => {
    const collected = new Set<AcademicResource>(extras);
    for (const field of config.fields) {
      if (field.reference) collected.add(field.reference);
    }
    for (const column of config.columns) {
      if (column.reference) collected.add(column.reference);
      if (column.reference === "formations") collected.add("parcours");
    }
    if (config.parcoursFilter) collected.add("parcours");
    if (config.formationFilter) collected.add("formations");
    if (config.specialisationFilter) collected.add("specialisations");
    if (config.hierarchyContext) {
      collected.add(config.hierarchyContext.reference);
      collected.add(config.hierarchyContext.parentReference);
    }
    return [...collected].sort();
  }, [config, extras]);
  const resourceKey = resources.join("|");
  const [data, setData] = useState<ReferenceData>({});
  const [loading, setLoading] = useState(resources.length > 0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    if (resources.length === 0) {
      setLoading(false);
      return () => {
        active = false;
      };
    }
    setLoading(true);
    setError(null);
    void Promise.all(
      resources.map(async (resource) => {
        const page = await adminApi.list(resource, { pageSize: 100, includeInactive: true });
        return [resource, page.items] as const;
      }),
    )
      .then((entries) => {
        if (active) setData(Object.fromEntries(entries) as ReferenceData);
      })
      .catch((reason) => {
        if (active) setError(errorMessage(reason));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
    // resourceKey represents the stable, sorted resource set.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resourceKey]);

  return { data, loading, error };
}
