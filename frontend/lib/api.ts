import type { HomePayload } from "./types";

const apiBase = resolveApiBase();

function resolveApiBase() {
  const configuredBase = process.env.NEXT_PUBLIC_API_BASE || process.env.API_BASE;

  if (configuredBase) {
    return configuredBase.replace(/\/$/, "");
  }

  if (process.env.NODE_ENV !== "production") {
    return "http://localhost:8000/api/v1";
  }

  throw new Error("Missing API base URL. Set NEXT_PUBLIC_API_BASE before running the frontend.");
}

export async function fetchHomePayload(): Promise<HomePayload> {
  const response = await fetch(`${apiBase}/home`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Failed to load home payload");
  }

  return response.json();
}

export async function createClaim(jobId: number, claimerName: string) {
  const response = await fetch(`${apiBase}/claims`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      job_id: jobId,
      claimer_name: claimerName,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to create claim");
  }

  return response.json();
}
