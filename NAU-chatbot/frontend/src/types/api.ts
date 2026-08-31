export interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
  detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
