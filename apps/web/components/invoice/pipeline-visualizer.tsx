"use client"

import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileSearch,
  Fingerprint,
  FileText,
  Database,
  ShieldCheck,
  Search,
  Send,
  Layers,
  MinusCircle,
  Bot,
} from "lucide-react"

import type { PipelineStepState, StepStatus } from "@/lib/invoice-types"

interface PipelineVisualizerProps {
  steps: PipelineStepState[]
  activeStepId: string | null
  isProcessing: boolean
}

const STEP_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  doc_reader: FileSearch,
  dedup_file: Fingerprint,
  extract: FileText,
  dedup_exact: Database,
  validate: ShieldCheck,
  anomaly_detect: Search,
  embed: Layers,
  respond: Send,
}

const STEP_ORDER = [
  "doc_reader",
  "dedup_file",
  "extract",
  "dedup_exact",
  "validate",
  "anomaly_detect",
  "embed",
  "respond",
] as const

function StatusIcon({ status }: { status: StepStatus }) {
  switch (status) {
    case "success":
      return <CheckCircle2 className="h-4 w-4 text-emerald-500" />
    case "warning":
      return <AlertTriangle className="h-4 w-4 text-amber-500" />
    case "error":
      return <XCircle className="h-4 w-4 text-red-500" />
    case "skipped":
      return <MinusCircle className="h-4 w-4 text-muted-foreground" />
    case "running":
      return (
        <div className="relative h-4 w-4">
          <div className="absolute inset-0 animate-ping rounded-full bg-primary/40" />
          <div className="relative h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      )
    default:
      return <div className="h-4 w-4 rounded-full border-2 border-muted-foreground/30" />
  }
}

function statusColor(status: StepStatus, isActive: boolean): string {
  if (isActive && status === "running") {
    return "border-primary bg-primary/10 shadow-lg shadow-primary/20 ring-2 ring-primary/30 ring-offset-2 ring-offset-background"
  }
  switch (status) {
    case "running":
      return "border-primary bg-primary/5 shadow-md shadow-primary/10"
    case "success":
      return "border-emerald-500/50 bg-emerald-500/5"
    case "warning":
      return "border-amber-500/50 bg-amber-500/5"
    case "error":
      return "border-red-500/50 bg-red-500/5"
    case "skipped":
      return "border-dashed border-muted-foreground/30 bg-muted/10 opacity-55"
    default:
      return "border-muted-foreground/20 bg-muted/20 opacity-50"
  }
}

function lineColor(status: StepStatus): string {
  switch (status) {
    case "success":
      return "bg-emerald-500"
    case "warning":
      return "bg-amber-500"
    case "error":
      return "bg-red-500"
    case "running":
      return "bg-primary animate-pulse"
    case "skipped":
      return "bg-muted-foreground/25"
    default:
      return "bg-muted-foreground/20"
  }
}

export function PipelineVisualizer({ steps, activeStepId, isProcessing }: PipelineVisualizerProps) {
  const stepMap = new Map(steps.map((s) => [s.id, s]))
  const orderedSteps = STEP_ORDER.map((id) => stepMap.get(id)).filter(
    (s): s is PipelineStepState => s != null,
  )

  const completed = orderedSteps.filter(
    (s) =>
      s.status === "success" ||
      s.status === "warning" ||
      s.status === "error" ||
      s.status === "skipped",
  ).length
  const progress =
    orderedSteps.length > 0 ? Math.round((completed / orderedSteps.length) * 100) : 0

  const activeStep = steps.find((s) => s.id === activeStepId)

  return (
    <div className="flex h-full w-full max-w-xs flex-col items-center justify-center gap-0 py-4">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Agent Pipeline
      </h3>

      {isProcessing && (
        <div className="mb-4 w-full max-w-[13rem] space-y-2 px-1">
          <div className="flex items-center justify-between text-[10px] text-muted-foreground">
            <span>Progress</span>
            <span className="font-mono font-medium text-foreground">{progress}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {activeStep && isProcessing && (
        <div className="mb-4 flex w-full max-w-[13rem] items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-2.5 py-2 shadow-sm">
          <div className="relative flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/15">
            <Bot className="h-3.5 w-3.5 text-primary" />
            <span className="absolute -right-0.5 -top-0.5 flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
            </span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[10px] font-medium uppercase tracking-wide text-primary">
              Active agent
            </p>
            <p className="truncate text-xs font-semibold">{activeStep.label}</p>
            {activeStep.message && (
              <p className="truncate text-[10px] text-muted-foreground">{activeStep.message}</p>
            )}
          </div>
        </div>
      )}

      {orderedSteps.map((step, i) => (
        <div key={step.id} className="flex flex-col items-center">
          <StepNode step={step} isActive={activeStepId === step.id} />
          {i < orderedSteps.length - 1 && (
            <ConnectorLine
              status={
                step.status === "skipped" ? "skipped" : step.status
              }
            />
          )}
        </div>
      ))}
    </div>
  )
}

function StepNode({ step, isActive }: { step: PipelineStepState; isActive: boolean }) {
  const Icon = STEP_ICONS[step.id] || FileText

  return (
    <div
      className={`relative flex w-56 items-center gap-3 rounded-xl border-2 px-3 py-2.5 transition-all duration-500 ${statusColor(step.status, isActive)}`}
    >
      {step.status === "running" && (
        <span className="absolute -right-1 -top-1 rounded-full bg-primary px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wide text-primary-foreground shadow-sm">
          Active
        </span>
      )}
      {step.status === "skipped" && (
        <span className="absolute -right-1 -top-1 rounded-full border bg-muted px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wide text-muted-foreground">
          Skip
        </span>
      )}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
          step.status === "running" ? "bg-primary/15" : "bg-background/80"
        }`}
      >
        <Icon
          className={`h-4 w-4 ${step.status === "running" ? "text-primary" : ""}`}
        />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-semibold">{step.label}</p>
        {step.message && (
          <p className="truncate text-[10px] text-muted-foreground">{step.message}</p>
        )}
      </div>
      <StatusIcon status={step.status} />
    </div>
  )
}

function ConnectorLine({ status }: { status: StepStatus }) {
  return (
    <div className="flex h-6 items-center justify-center">
      <div className={`h-full w-0.5 rounded-full transition-all duration-500 ${lineColor(status)}`} />
    </div>
  )
}
