import { createSentrixRepository } from "./domain.js";
import { createApiRepository } from "./apiRepository.js";

export function selectedMode() {
  if (typeof window === "undefined" || !window.location) return "api";
  const params = new URLSearchParams(window.location.search);
  return params.get("repo") === "memory" ? "memory" : "api";
}

export async function createRepository(options = {}) {
  const mode = options.mode ?? selectedMode();
  if (mode === "memory") return createSentrixRepository();
  try {
    return await createApiRepository();
  } catch (error) {
    if (String(error?.message).includes("AUTH_REQUIRED")) throw error;
    console.warn("SENTRIX API unavailable; using in-memory demo data.", error);
    return createSentrixRepository();
  }
}
