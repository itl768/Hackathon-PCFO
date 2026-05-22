"use client"

import { useState } from "react"
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronRight } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import {
  STAGE_LABELS,
  type Finding,
  type ReviewSummary,
  type StageName,
} from "@/lib/types"

interface SummaryPanelProps {
  summary: ReviewSummary | null
  anomalies: Finding[]
  validationErrors: Finding[]
  agentOutputs: Record<string, Record<string, unknown>>
}

export function SummaryPanel({
  summary,
  anomalies,
  validationErrors,
  agentOutputs,
}: SummaryPanelProps) {
  const isGood = summary?.verdict === "good"
  const extractorMeta = readAgentMeta(agentOutputs.extractor)
  const responderMeta = readAgentMeta(agentOutputs.responder)

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Review Summary
      </h2>

      <div
        className={cn(
          "flex items-start gap-3 rounded-md border px-3 py-3",
          isGood
            ? "border-emerald-500/40 bg-emerald-500/5"
            : "border-amber-500/40 bg-amber-500/5"
        )}
      >
        {isGood ? (
          <CheckCircle2 className="mt-0.5 size-5 text-emerald-500" />
        ) : (
          <AlertTriangle className="mt-0.5 size-5 text-amber-500" />
        )}
        <div className="flex flex-col gap-1">
          <div className="text-sm font-medium">
            {summary ? (isGood ? "Looks good" : "Needs review") : "Waiting for Responder..."}
          </div>
          <div className="text-sm text-muted-foreground">
            {summary?.text || "Summary will appear once the Responder completes."}
          </div>
          {summary && (
            <div className="mt-1 flex gap-2 text-xs text-muted-foreground">
              <Badge variant={anomalies.length > 0 ? "destructive" : "secondary"}>
                {anomalies.length} anomal{anomalies.length === 1 ? "y" : "ies"}
              </Badge>
              <Badge variant={validationErrors.length > 0 ? "destructive" : "secondary"}>
                {validationErrors.length} validation issue
                {validationErrors.length === 1 ? "" : "s"}
              </Badge>
            </div>
          )}
        </div>
      </div>

      {(extractorMeta || responderMeta) && (
        <div className="flex flex-col gap-2 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          {extractorMeta && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="font-medium text-foreground/80">Extractor</span>
              <span>
                Model: <span className="font-mono text-foreground">{extractorMeta.model}</span>
              </span>
              {extractorMeta.latencyMs !== null && (
                <span>
                  Latency:{" "}
                  <span className="font-mono text-foreground">{extractorMeta.latencyMs} ms</span>
                </span>
              )}
              {extractorMeta.fieldCount !== null && (
                <span>
                  Fields:{" "}
                  <span className="font-mono text-foreground">{extractorMeta.fieldCount}</span>
                </span>
              )}
            </div>
          )}
          {responderMeta && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="font-medium text-foreground/80">Responder</span>
              <span>
                Model: <span className="font-mono text-foreground">{responderMeta.model}</span>
              </span>
              {responderMeta.latencyMs !== null && (
                <span>
                  Latency:{" "}
                  <span className="font-mono text-foreground">{responderMeta.latencyMs} ms</span>
                </span>
              )}
            </div>
          )}
        </div>
      )}

      <FindingsList title="Anomalies" findings={anomalies} emptyText="No anomalies detected" />
      <FindingsList
        title="Validation issues"
        findings={validationErrors}
        emptyText="No validation issues"
      />

      <AgentActivity agentOutputs={agentOutputs} />
    </div>
  )
}

interface AgentMeta {
  model: string
  latencyMs: number | null
  fieldCount: number | null
}

function readAgentMeta(output: Record<string, unknown> | undefined): AgentMeta | null {
  if (!output) return null
  const model = typeof output.model === "string" ? output.model : null
  if (!model) return null
  const latencyMs = typeof output.latency_ms === "number" ? output.latency_ms : null
  const fieldCount = typeof output.field_count === "number" ? output.field_count : null
  return { model, latencyMs, fieldCount }
}

function FindingsList({
  title,
  findings,
  emptyText,
}: {
  title: string
  findings: Finding[]
  emptyText: string
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </div>
      {findings.length === 0 ? (
        <div className="text-xs italic text-muted-foreground">{emptyText}</div>
      ) : (
        <ul className="space-y-1.5">
          {findings.map((finding, idx) => (
            <li
              key={`${finding.source_agent}-${idx}`}
              className="rounded-md border border-border bg-card px-2.5 py-1.5 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-muted-foreground">{finding.field_path}</span>
                <Badge variant="outline" className="text-[10px]">
                  {finding.severity}
                </Badge>
              </div>
              <div className="mt-1 text-sm">{finding.message}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function AgentActivity({
  agentOutputs,
}: {
  agentOutputs: Record<string, Record<string, unknown>>
}) {
  const [expanded, setExpanded] = useState(false)
  const entries = Object.entries(agentOutputs) as [StageName, Record<string, unknown>][]

  return (
    <div className="flex flex-col gap-1.5">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground"
      >
        {expanded ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
        Agent activity ({entries.length})
      </button>
      {expanded && (
        <div className="space-y-1.5">
          {entries.length === 0 ? (
            <div className="text-xs italic text-muted-foreground">
              No agent activity recorded yet.
            </div>
          ) : (
            entries.map(([name, output]) => (
              <details
                key={name}
                className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs"
              >
                <summary className="cursor-pointer text-sm font-medium">
                  {STAGE_LABELS[name] ?? name}
                </summary>
                <pre className="mt-2 overflow-x-auto rounded-md bg-background/50 p-2 text-[11px]">
                  {JSON.stringify(output, null, 2)}
                </pre>
              </details>
            ))
          )}
        </div>
      )}
    </div>
  )
}
