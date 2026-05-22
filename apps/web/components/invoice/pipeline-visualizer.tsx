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
} from "lucide-react"

import type { PipelineStepState, StepStatus } from "@/lib/invoice-types"

interface PipelineVisualizerProps {
  steps: PipelineStepState[]
}

const STEP_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  doc_reader: FileSearch,
  dedup_vector: Fingerprint,
  extract: FileText,
  dedup_exact: Database,
  validate: ShieldCheck,
  anomaly_detect: Search,
  respond: Send,
}

function StatusIcon({ status }: { status: StepStatus }) {
  switch (status) {
    case "success":
      return <CheckCircle2 className="h-4 w-4 text-emerald-500" />
    case "warning":
      return <AlertTriangle className="h-4 w-4 text-amber-500" />
    case "error":
      return <XCircle className="h-4 w-4 text-red-500" />
    case "running":
      return (
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      )
    default:
      return <div className="h-4 w-4 rounded-full border-2 border-muted-foreground/30" />
  }
}

function statusColor(status: StepStatus): string {
  switch (status) {
    case "running":
      return "border-primary bg-primary/5 shadow-lg shadow-primary/10"
    case "success":
      return "border-emerald-500/50 bg-emerald-500/5"
    case "warning":
      return "border-amber-500/50 bg-amber-500/5"
    case "error":
      return "border-red-500/50 bg-red-500/5"
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
    default:
      return "bg-muted-foreground/20"
  }
}

export function PipelineVisualizer({ steps }: PipelineVisualizerProps) {
  const mainSteps = steps.filter((s) => s.id !== "validate" && s.id !== "anomaly_detect")
  const validateStep = steps.find((s) => s.id === "validate")
  const anomalyStep = steps.find((s) => s.id === "anomaly_detect")
  const respondStep = steps.find((s) => s.id === "respond")

  const beforeParallel = mainSteps.filter(
    (s) => s.id !== "respond" && s.id !== "validate" && s.id !== "anomaly_detect",
  )

  return (
    <div className="flex h-full flex-col items-center justify-center gap-0 py-4">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Agent Pipeline
      </h3>

      {/* Sequential steps before parallel */}
      {beforeParallel.map((step, i) => (
        <div key={step.id} className="flex flex-col items-center">
          <StepNode step={step} />
          {i < beforeParallel.length - 1 && <ConnectorLine status={step.status} />}
        </div>
      ))}

      {/* Fan-out connector */}
      {validateStep && anomalyStep && (
        <>
          <ConnectorLine status={beforeParallel[beforeParallel.length - 1]?.status ?? "idle"} />
          <div className="flex items-start gap-6">
            {/* Left branch: Validator */}
            <div className="flex flex-col items-center">
              <div className="mb-1 h-4 w-px bg-muted-foreground/20" />
              <StepNode step={validateStep} />
            </div>

            {/* Right branch: Anomaly */}
            <div className="flex flex-col items-center">
              <div className="mb-1 h-4 w-px bg-muted-foreground/20" />
              <StepNode step={anomalyStep} />
            </div>
          </div>
          {/* Fan-in connector */}
          <div className="my-1 h-4 w-px bg-muted-foreground/20" />
        </>
      )}

      {/* Responder */}
      {respondStep && <StepNode step={respondStep} />}
    </div>
  )
}

function StepNode({ step }: { step: PipelineStepState }) {
  const Icon = STEP_ICONS[step.id] || FileText

  return (
    <div
      className={`flex w-52 items-center gap-3 rounded-xl border-2 px-3 py-2.5 transition-all duration-500 ${statusColor(step.status)}`}
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-background/80">
        <Icon className="h-4 w-4" />
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
