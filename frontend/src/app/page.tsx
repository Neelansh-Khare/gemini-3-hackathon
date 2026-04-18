"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { getAudit, getGraph, postApprove, postIntent, postResetDemo, postRollback, type ToolOperation } from "@/lib/api";
import type { z } from "zod";
import { IntentResponseSchema } from "@/lib/schemas";

type IntentResponse = z.infer<typeof IntentResponseSchema>;

type AuditEntry = {
  id: string;
  timestamp: string;
  connector: string;
  operation: string;
  payload_summary: string;
};

type GraphData = {
  nodes: Array<{ id: string; type: string; title: string; description: string }>;
  edges: Array<{ source: string; target: string; type: string }>;
};

function VisualDiff({ op }: { op: ToolOperation }) {
  const p = op.payload;
  if (op.connector === "calendar") {
    return (
      <div className="mt-2 space-y-1 text-[10px] text-zinc-400">
        <div className="flex justify-between">
          <span className="text-zinc-500">Title:</span>{" "}
          <span className="text-zinc-300">{p.title}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-zinc-500">When:</span> <span>{p.start || "—"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-zinc-500">Where:</span> <span>{p.location || "—"}</span>
        </div>
      </div>
    );
  }
  if (op.connector === "gmail") {
    return (
      <div className="mt-2 space-y-1 text-[10px] text-zinc-400">
        <div className="flex justify-between">
          <span className="text-zinc-500">To:</span> <span className="text-zinc-300">{p.to || "—"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-zinc-500">Subject:</span>{" "}
          <span className="font-medium text-zinc-300">{p.subject}</span>
        </div>
        <div className="mt-1 max-h-24 overflow-auto border-t border-zinc-800 pt-1 text-zinc-500 italic">
          {p.body}
        </div>
      </div>
    );
  }
  if (op.connector === "notion") {
    return (
      <div className="mt-2 space-y-1 text-[10px] text-zinc-400">
        <div className="flex justify-between">
          <span className="text-zinc-500">Item:</span>{" "}
          <span className="text-zinc-300">{p.title}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-zinc-500">Type:</span> <span>{p.type || p.item_type || "task"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-zinc-500">Status:</span> <span>{p.status || "todo"}</span>
        </div>
      </div>
    );
  }
  if (op.connector === "obsidian") {
    return (
      <div className="mt-2 space-y-1 text-[10px] text-zinc-400">
        <div className="flex justify-between">
          <span className="text-zinc-500">File:</span>{" "}
          <span className="text-indigo-300">{p.path}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-zinc-500">Section:</span> <span>{p.section}</span>
        </div>
        <div className="mt-1 max-h-20 overflow-auto border-t border-zinc-800 pt-1 whitespace-pre-wrap text-[9px] text-zinc-500">
          {p.body}
        </div>
      </div>
    );
  }
  return (
    <pre className="mt-2 max-h-28 overflow-auto rounded bg-black/40 p-2 text-[10px] leading-relaxed text-zinc-500">
      {JSON.stringify(op.payload, null, 2)}
    </pre>
  );
}

function GraphView({ data }: { data: GraphData }) {
  if (!data.nodes.length) return <p className="text-zinc-500">Graph is empty.</p>;

  return (
    <div className="h-[320px] w-full overflow-hidden rounded-lg border border-zinc-800 bg-black/20 flex flex-col">
      <ScrollArea className="flex-1 p-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {data.nodes.map((node) => (
            <div
              key={node.id}
              className="flex flex-col rounded-md border border-zinc-800 bg-zinc-900/60 p-2 shadow-sm"
            >
              <div className="flex items-center justify-between gap-1">
                <span className="text-[9px] font-bold uppercase text-indigo-400/80">{node.type}</span>
                <span className="h-1.5 w-1.5 rounded-full bg-indigo-500/50" />
              </div>
              <span className="mt-1 line-clamp-1 text-[10px] font-medium text-zinc-200">{node.title}</span>
              <span className="mt-0.5 line-clamp-2 text-[9px] text-zinc-500">{node.description}</span>
            </div>
          ))}
        </div>
      </ScrollArea>
      <div className="border-t border-zinc-800 bg-zinc-900/40 p-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400 mb-2">Active Relations</p>
        <ScrollArea className="h-20">
          <div className="space-y-1.5">
            {data.edges.map((edge, i) => (
              <div key={i} className="flex items-center gap-2 text-[9px] text-zinc-500">
                <span className="text-zinc-300 font-mono">{edge.source.replace(/^[^_]+_/, '')}</span>
                <span className="px-1 py-0.5 rounded bg-zinc-800 text-indigo-400 text-[8px] uppercase">{edge.type}</span>
                <span className="text-zinc-300 font-mono">{edge.target.replace(/^[^_]+_/, '')}</span>
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}

export default function Home() {
  const [intentText, setIntentText] = useState(
    "Plan my next week around my meetings, deadlines, workouts, and follow-ups",
  );
  const [loading, setLoading] = useState(false);
  const [execLoading, setExecLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<IntentResponse | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [graphData, setGraphData] = useState<GraphData | null>(null);

  const loadAudit = useCallback(async () => {
    try {
      const data = await getAudit(50);
      const entries = (data.entries ?? []) as AuditEntry[];
      setAudit(entries);
    } catch {
      setAudit([]);
    }
  }, []);

  const loadGraph = useCallback(async () => {
    try {
      const data = await getGraph();
      setGraphData(data);
    } catch {
      setGraphData(null);
    }
  }, []);

  useEffect(() => {
    void loadAudit();
    void loadGraph();
  }, [loadAudit, loadGraph]);

  const runIntent = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await postIntent(intentText);
      const parsed = IntentResponseSchema.safeParse(data);
      setResult(parsed.success ? parsed.data : (data as IntentResponse));
      const ops = (parsed.success ? parsed.data : (data as IntentResponse)).tool_operations;
      setSelectedIds(new Set(ops.map((o) => o.id)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const toggleOp = (id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const approveAll = () => {
    if (!result) return;
    setSelectedIds(new Set(result.tool_operations.map((o) => o.id)));
  };

  const rejectAll = () => {
    setSelectedIds(new Set());
  };

  const executeSelected = async () => {
    if (!result) return;
    const ops = result.tool_operations.filter((o) => selectedIds.has(o.id));
    if (ops.length === 0) {
      setError("Select at least one operation to execute.");
      return;
    }
    setExecLoading(true);
    setError(null);
    try {
      await postApprove(ops as ToolOperation[]);
      await loadAudit();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Execute failed");
    } finally {
      setExecLoading(false);
    }
  };

  const rollbackEntry = async (id: string) => {
    setExecLoading(true);
    try {
      await postRollback([id]);
      await loadAudit();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rollback failed");
    } finally {
      setExecLoading(false);
    }
  };

  const resetDemo = async () => {
    setExecLoading(true);
    try {
      await postResetDemo();
      setResult(null);
      setSelectedIds(new Set());
      await loadAudit();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setExecLoading(false);
    }
  };

  const recommended = result?.recommended_plan;
  const council = result?.council_recommendation as Record<string, unknown> | undefined;

  const scoreLine = useMemo(() => {
    const scores = council?.scores as Record<string, Record<string, number>> | undefined;
    if (!scores || !recommended) return null;
    const s = scores[recommended.id];
    if (!s) return null;
    return `Skeptic ${s.skeptic ?? "—"} · Optimizer ${s.optimizer ?? "—"} · Privacy ${s.privacy ?? "—"}`;
  }, [council, recommended]);

  return (
    <main className="mx-auto min-h-screen max-w-[1600px] p-6 md:p-10">
      <header className="mb-10 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="mb-1 flex items-center gap-2 text-indigo-400">
            <Sparkles className="h-5 w-5" />
            <span className="text-xs font-semibold uppercase tracking-widest">Life OS</span>
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-50 md:text-4xl">
            Planning & execution workspace
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-zinc-400">
            Natural language in → retrieval from your tools → council plans → diff preview → you approve → writes
            execute. No silent overwrites; drafts only for email.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void loadAudit()} disabled={execLoading}>
            <RefreshCw className="h-4 w-4" /> Refresh audit
          </Button>
          <Button variant="ghost" size="sm" onClick={() => void resetDemo()} disabled={execLoading}>
            Reset demo data
          </Button>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        {/* Left column: chat + context */}
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Request</CardTitle>
              <CardDescription>High-level intent (demo flow from PRD)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea
                value={intentText}
                onChange={(e) => setIntentText(e.target.value)}
                placeholder="What should Life OS plan?"
              />
              <Button variant="primary" className="w-full" onClick={() => void runIntent()} disabled={loading}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Run orchestration
              </Button>
              {error ? <p className="text-sm text-red-400">{error}</p> : null}
            </CardContent>
          </Card>

          <Card className="min-h-[280px] flex-1">
            <CardHeader>
              <CardTitle>Context drawer</CardTitle>
              <CardDescription>Items retrieved for reasoning (ranked)</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[320px] pr-3">
                <ul className="space-y-3 text-sm">
                  {result?.context_packet.items?.length ? (
                    result.context_packet.items.map((it) => (
                      <li
                        key={it.id}
                        className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium text-zinc-200">{it.title}</span>
                          <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
                            {it.source}
                          </span>
                        </div>
                        <p className="mt-1 line-clamp-3 text-zinc-500">{it.body}</p>
                        <p className="mt-1 text-xs text-zinc-600">
                          relevance {(it.relevance * 100).toFixed(0)}% · importance{" "}
                          {(it.importance * 100).toFixed(0)}%
                        </p>
                      </li>
                    ))
                  ) : (
                    <li className="text-zinc-500">Run a request to load calendar, Gmail, Notion, and Obsidian context.</li>
                  )}
                </ul>
              </ScrollArea>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>LifeGraph Visualization</CardTitle>
              <CardDescription>Knowledge graph of entities & relations</CardDescription>
            </CardHeader>
            <CardContent>
              {graphData ? <GraphView data={graphData} /> : <p className="text-sm text-zinc-500">Loading graph...</p>}
            </CardContent>
          </Card>
        </div>

        {/* Right column: plans + diff + approval */}
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Reasoning & council</CardTitle>
              <CardDescription>Summary from planner + council scoring</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p className="text-zinc-300">{result?.summary ?? "—"}</p>
              {result?.warnings?.length ? (
                <ul className="list-inside list-disc text-amber-400">
                  {result.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              ) : null}
              {scoreLine ? <p className="text-xs text-zinc-500">{scoreLine}</p> : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Candidate plans</CardTitle>
              <CardDescription>2–3 alternative strategies</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {result?.candidate_plans?.length ? (
                result.candidate_plans.map((p) => (
                  <div
                    key={p.id}
                    className={`rounded-lg border p-3 ${
                      p.id === result.recommended_plan_id
                        ? "border-indigo-500/60 bg-indigo-950/20"
                        : "border-zinc-800 bg-zinc-900/40"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-medium text-zinc-200">{p.title}</p>
                        <p className="mt-1 text-xs text-zinc-500">{p.summary}</p>
                      </div>
                      <span className="shrink-0 rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
                        {p.estimated_effort}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-zinc-600">
                      Risks: {p.risks.join("; ") || "—"} · Benefits: {p.benefits.join("; ") || "—"}
                    </p>
                    {result.council_recommendation?.scores?.[p.id] && (
                      <div className="mt-2 flex gap-3 text-[10px]">
                        <span className="text-zinc-500">
                          Skeptic:{" "}
                          <span className="text-zinc-300">
                            {result.council_recommendation.scores[p.id].skeptic}/10
                          </span>
                        </span>
                        <span className="text-zinc-500">
                          Optimizer:{" "}
                          <span className="text-zinc-300">
                            {result.council_recommendation.scores[p.id].optimizer}/10
                          </span>
                        </span>
                        <span className="text-zinc-500">
                          Privacy:{" "}
                          <span className="text-zinc-300">
                            {result.council_recommendation.scores[p.id].privacy}/10
                          </span>
                        </span>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <p className="text-sm text-zinc-500">No plans yet.</p>
              )}
            </CardContent>
          </Card>

          {recommended ? (
            <Card className="border-indigo-500/40">
              <CardHeader>
                <CardTitle>Recommended plan</CardTitle>
                <CardDescription>Why this plan: {recommended.summary}</CardDescription>
              </CardHeader>
              <CardContent>
                <ol className="list-inside list-decimal space-y-1 text-sm text-zinc-400">
                  {recommended.steps.map((s, i) => (
                    <li key={i}>
                      <span className="text-zinc-500">[{s.target_system}]</span> {s.description}
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>Diff preview</CardTitle>
              <CardDescription>Concrete writes before execution (approval-gated)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <ScrollArea className="h-[320px] pr-3">
                <ul className="space-y-2">
                  {result?.tool_operations?.length ? (
                    result.tool_operations.map((op) => (
                      <li
                        key={op.id}
                        className="flex gap-3 rounded-lg border border-zinc-800 bg-zinc-900/60 p-3 text-sm"
                      >
                        <Checkbox
                          checked={selectedIds.has(op.id)}
                          onCheckedChange={(c) => toggleOp(op.id, c === true)}
                          className="mt-0.5"
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-indigo-300">
                              {op.connector}
                            </span>
                            <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
                              {op.operation}
                            </span>
                          </div>
                          <p className="mt-1 font-mono text-xs text-zinc-300">{op.preview}</p>
                          <VisualDiff op={op} />
                        </div>
                      </li>
                    ))
                  ) : (
                    <li className="text-zinc-500">No tool operations yet.</li>
                  )}
                </ul>
              </ScrollArea>
              <Separator />
              <div className="flex flex-wrap gap-2">
                <Button variant="primary" size="sm" onClick={approveAll}>
                  Approve all
                </Button>
                <Button variant="outline" size="sm" onClick={rejectAll}>
                  Reject all
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => void executeSelected()}
                  disabled={execLoading || !result?.tool_operations?.length}
                >
                  {execLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  Execute selected
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Audit log</CardTitle>
              <CardDescription>Executed actions (append-only audit trail)</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[200px] pr-3">
                <ul className="space-y-2 text-xs text-zinc-400">
                  {audit.length ? (
                    audit.map((a) => (
                      <li key={a.id} className="group relative rounded border border-zinc-800 p-2">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <span className="text-zinc-500">{a.timestamp}</span>{" "}
                            <span className="text-indigo-400">{a.connector}</span> · {a.operation}
                            <p className="mt-1 text-zinc-500">{a.payload_summary}</p>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-[10px] opacity-0 group-hover:opacity-100"
                            onClick={() => void rollbackEntry(a.id)}
                            disabled={execLoading}
                          >
                            Undo
                          </Button>
                        </div>
                      </li>
                    ))
                  ) : (
                    <li className="text-zinc-600">No executions yet.</li>
                  )}
                </ul>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
