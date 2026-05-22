"use client"

import { CheckCircle2, CircleDashed, Loader2, MinusCircle, XCircle } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  STAGE_LABELS,
  type StageName,
  type StageState,
  type StageStatus,
} from "@/lib/types"

interface InvoiceTimelineProps {
  stages: Record<StageName, StageState>
  duplicateMode: boolean
}

interface TimelineRow {
  stage: StageName
  parallel?: StageName
  indented?: boolean
}

const STANDARD_ROWS: TimelineRow[] = [
  { stage: "extractor" },
  { stage: "deduplication" },
  { stage: "anomaly_detector", indented: true, parallel: "validator" },
  { stage: "validator", indented: true, parallel: "anomaly_detector" },
  { stage: "responder" },
]

const DUPLICATE_ROWS: TimelineRow[] = [
  { stage: "extractor" },
  { stage: "deduplication" },
  { stage: "duplicate_handler" },
]

export function InvoiceTimeline({ stages, duplicateMode }: InvoiceTimelineProps) {
  const rows = duplicateMode ? DUPLICATE_ROWS : STANDARD_ROWS

  return (
    <div className="flex flex-col gap-1">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Pipeline Progress
      </h2>
      <ul className="space-y-1">
        {rows.map((row) => {
          const stage = stages[row.stage]
          return (
            <li
              key={row.stage}
              className={cn(
                "flex items-center gap-3 rounded-md border border-border bg-card px-3 py-2",
                row.indented && "ml-4"
              )}
            >
              <StatusIcon status={stage.status} />
              <div className="flex flex-1 flex-col">
                <div className="text-sm font-medium">{STAGE_LABELS[row.stage]}</div>
                <div className="text-xs text-muted-foreground">
                  {statusDescription(stage.status, row.parallel)}
                </div>
              </div>
            </li>
          )
        })}
      </ul>
      {!duplicateMode && (
        <div className="mt-2 text-xs text-muted-foreground">
          Anomaly Detector and Validator run in parallel after Deduplication and converge on the
          Responder.
        </div>
      )}
    </div>
  )
}

function StatusIcon({ status }: { status: StageStatus }) {
  switch (status) {
    case "running":
      return <Loader2 className="size-4 animate-spin text-primary" />
    case "completed":
      return <CheckCircle2 className="size-4 text-emerald-500" />
    case "failed":
      return <XCircle className="size-4 text-destructive" />
    case "skipped":
      return <MinusCircle className="size-4 text-muted-foreground" />
    default:
      return <CircleDashed className="size-4 text-muted-foreground" />
  }
}

function statusDescription(status: StageStatus, parallel: StageName | undefined): string {
  switch (status) {
    case "running":
      return parallel
        ? `Running in parallel with ${STAGE_LABELS[parallel]}`
        : "Running..."
    case "completed":
      return "Completed"
    case "failed":
      return "Failed"
    case "skipped":
      return "Skipped"
    default:
      return parallel ? `Queued (will run with ${STAGE_LABELS[parallel]})` : "Queued"
  }
}
