const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

export const API_BASE_URL = (configuredBaseUrl || "/api/v1").replace(/\/$/, "");

export const CHAT_MESSAGE_MAX_LENGTH = 4_000;
export const ADMIN_PAGE_SIZE = 20;
