import { ApiError } from "../api/http";

export function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Une erreur inattendue est survenue. Réessayez.";
}
