import type { z } from "zod";
import { AuditListSchema, IntentResponseSchema, ToolOperationSchema } from "./schemas";

export type ToolOperation = z.infer<typeof ToolOperationSchema>;

export function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
}

export async function postIntent(intent: string) {
  const res = await fetch(`${getApiBase()}/intent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intent }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `HTTP ${res.status}`);
  }
  const data = await res.json();
  const parsed = IntentResponseSchema.safeParse(data);
  if (!parsed.success) {
    console.warn("Intent response parse warning", parsed.error.flatten());
    return data as unknown as z.infer<typeof IntentResponseSchema>;
  }
  return parsed.data;
}

export async function postApprove(tool_operations: ToolOperation[]) {
  const res = await fetch(`${getApiBase()}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tool_operations }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `HTTP ${res.status}`);
  }
  return res.json() as Promise<{ executed: unknown[] }>;
}

export async function getAudit(limit = 100) {
  const res = await fetch(`${getApiBase()}/audit?limit=${limit}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Audit ${res.status}`);
  const data = await res.json();
  const parsed = AuditListSchema.safeParse(data);
  if (!parsed.success) {
    return data as { entries: unknown[] };
  }
  return parsed.data;
}

export async function postRollback(entry_ids: string[]) {
  const res = await fetch(`${getApiBase()}/rollback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entry_ids }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `HTTP ${res.status}`);
  }
  return res.json() as Promise<{ rolled_back: unknown[] }>;
}

export async function postResetDemo() {
  const res = await fetch(`${getApiBase()}/demo/reset`, { method: "POST" });
  if (!res.ok) throw new Error(`Reset ${res.status}`);
  return res.json() as Promise<{ status: string }>;
}
