import type { Page } from "../types/api";
import type {
  AcademicEntity,
  AcademicOverviewResponse,
  AcademicResource,
  MutationResponse,
  OrientationMatrixResponse,
  RagQueueResponse,
  RagStatusResponse,
} from "../types/academic";
import { apiRequest } from "./http";

export interface AdminListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  includeInactive?: boolean;
  formationId?: number;
  specialisationId?: number;
}

function listQuery(params: AdminListParams): string {
  const query = new URLSearchParams();
  query.set("page", String(params.page ?? 1));
  query.set("page_size", String(params.pageSize ?? 20));
  if (params.search?.trim()) query.set("search", params.search.trim());
  if (params.includeInactive) query.set("include_inactive", "true");
  if (params.formationId) query.set("formation_id", String(params.formationId));
  if (params.specialisationId) query.set("specialisation_id", String(params.specialisationId));
  return query.toString();
}

export const adminApi = {
  list(resource: AcademicResource, params: AdminListParams = {}): Promise<Page<AcademicEntity>> {
    return apiRequest<Page<AcademicEntity>>(`/admin/${resource}?${listQuery(params)}`);
  },

  get(resource: AcademicResource, id: number): Promise<AcademicEntity> {
    return apiRequest<AcademicEntity>(`/admin/${resource}/${id}`);
  },

  create(resource: AcademicResource, payload: Record<string, unknown>): Promise<MutationResponse> {
    return apiRequest<MutationResponse>(`/admin/${resource}`, { method: "POST", body: payload });
  },

  update(
    resource: AcademicResource,
    id: number,
    payload: Record<string, unknown>,
  ): Promise<MutationResponse> {
    return apiRequest<MutationResponse>(`/admin/${resource}/${id}`, {
      method: "PATCH",
      body: payload,
    });
  },

  activate(resource: AcademicResource, id: number): Promise<MutationResponse> {
    return apiRequest<MutationResponse>(`/admin/${resource}/${id}/activate`, { method: "POST" });
  },

  deactivate(resource: AcademicResource, id: number): Promise<MutationResponse> {
    return apiRequest<MutationResponse>(`/admin/${resource}/${id}/deactivate`, { method: "POST" });
  },

  remove(resource: AcademicResource, id: number): Promise<MutationResponse> {
    return apiRequest<MutationResponse>(`/admin/${resource}/${id}`, { method: "DELETE" });
  },

  ragStatus(): Promise<RagStatusResponse> {
    return apiRequest<RagStatusResponse>("/admin/rag/status");
  },

  reindexAll(): Promise<RagQueueResponse> {
    return apiRequest<RagQueueResponse>("/admin/rag/reindex", { method: "POST" });
  },

  reindexFormation(formationId: number): Promise<RagQueueResponse> {
    return apiRequest<RagQueueResponse>(`/admin/rag/reindex/${formationId}`, { method: "POST" });
  },

  orientationMatrix(): Promise<OrientationMatrixResponse> {
    return apiRequest<OrientationMatrixResponse>("/admin/orientation-matrix");
  },

  academicOverview(includeInactive = false): Promise<AcademicOverviewResponse> {
    return apiRequest<AcademicOverviewResponse>(
      `/admin/academic-overview?include_inactive=${includeInactive ? "true" : "false"}`,
    );
  },
};
