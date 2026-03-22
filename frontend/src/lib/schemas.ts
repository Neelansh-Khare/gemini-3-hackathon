import { z } from "zod";

/** Mirrors backend `src/domain/prd_models.py` + orchestration JSON. */

export const ContextItemSchema = z.object({
  id: z.string(),
  source: z.enum(["gmail", "calendar", "notion", "obsidian"]),
  kind: z.string(),
  title: z.string(),
  body: z.string(),
  occurred_at: z.string().nullable().optional(),
  relevance: z.number(),
  importance: z.number(),
  metadata: z.record(z.string(), z.any()).optional(),
});

export const ContextPacketSchema = z.object({
  query: z.string(),
  items: z.array(ContextItemSchema),
  summary: z.string(),
  retrieved_at: z.string().optional(),
});

export const PlanStepSchema = z.object({
  type: z.enum(["schedule", "task", "communication", "note_update"]),
  description: z.string(),
  target_system: z.enum(["calendar", "notion", "gmail", "obsidian"]),
  priority: z.number(),
});

export const CandidatePlanSchema = z.object({
  id: z.string(),
  title: z.string(),
  summary: z.string(),
  steps: z.array(PlanStepSchema),
  risks: z.array(z.string()),
  benefits: z.array(z.string()),
  estimated_effort: z.enum(["low", "medium", "high"]),
});

export const ToolOperationSchema = z.object({
  id: z.string(),
  connector: z.enum(["gmail", "calendar", "notion", "obsidian"]),
  operation: z.enum(["create", "update", "append", "draft"]),
  target_id: z.string().nullable().optional(),
  preview: z.string(),
  payload: z.record(z.string(), z.any()),
  requires_approval: z.boolean(),
});

export const IntentResponseSchema = z.object({
  goal: z.string(),
  intent: z.record(z.string(), z.any()).optional(),
  context_packet: ContextPacketSchema,
  candidate_plans: z.array(CandidatePlanSchema),
  recommended_plan_id: z.string(),
  recommended_plan: CandidatePlanSchema,
  council_recommendation: z.record(z.string(), z.any()),
  tool_operations: z.array(ToolOperationSchema),
  approval_required: z.boolean(),
  summary: z.string(),
  warnings: z.array(z.string()),
});

export const AuditEntrySchema = z.object({
  id: z.string(),
  timestamp: z.string(),
  connector: z.enum(["gmail", "calendar", "notion", "obsidian"]),
  operation: z.enum(["create", "update", "append", "draft"]),
  target_id: z.string().nullable().optional(),
  payload_summary: z.string(),
  payload: z.record(z.string(), z.any()),
  tool_operation_id: z.string().nullable().optional(),
});

export const AuditListSchema = z.object({
  entries: z.array(AuditEntrySchema),
});
