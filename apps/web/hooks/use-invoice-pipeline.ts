"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import { subscribeToInvoiceEvents } from "@/lib/api"
import {
  type StageEvent,
  type StageName,
  type StageState,
  type StageStatus,
  STAGE_NAMES,
} from "@/lib/types"

interface PipelineState {
  stages: Record<StageName, StageState>
  currentStage: StageName | null
  isRunning: boolean
  finished: boolean
  duplicate: { matchedInvoiceId: string | null } | null
  error: string | null
}

function initialStageMap(): Record<StageName, StageState> {
  return STAGE_NAMES.reduce(
    (acc, name) => {
      acc[name] = { name, status: "queued" }
      return acc
    },
    {} as Record<StageName, StageState>
  )
}

function initialPipelineState(): PipelineState {
  return {
    stages: initialStageMap(),
    currentStage: null,
    isRunning: false,
    finished: false,
    duplicate: null,
    error: null,
  }
}

export function useInvoicePipeline(invoiceId: string | null) {
  const [state, setState] = useState<PipelineState>(initialPipelineState)
  const abortRef = useRef<AbortController | null>(null)

  const reset = useCallback(() => {
    setState(initialPipelineState())
  }, [])

  useEffect(() => {
    if (!invoiceId) {
      setState(initialPipelineState())
      return
    }

    setState({ ...initialPipelineState(), isRunning: true })
    const controller = new AbortController()
    abortRef.current = controller

    let cancelled = false
    ;(async () => {
      try {
        for await (const event of subscribeToInvoiceEvents(invoiceId, controller.signal)) {
          if (cancelled) break
          setState((prev) => applyEvent(prev, event))
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") return
        setState((prev) => ({
          ...prev,
          isRunning: false,
          error: err instanceof Error ? err.message : "Stream error",
        }))
      }
    })()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [invoiceId])

  return { ...state, reset }
}

function applyEvent(prev: PipelineState, event: StageEvent): PipelineState {
  switch (event.type) {
    case "invoice_received":
      return prev

    case "stage_started":
      if (!event.stage) return prev
      return {
        ...prev,
        currentStage: event.stage,
        isRunning: true,
        stages: updateStage(prev.stages, event.stage, {
          status: "running",
          startedAt: event.occurred_at,
        }),
      }

    case "stage_completed":
      if (!event.stage) return prev
      return {
        ...prev,
        stages: updateStage(prev.stages, event.stage, {
          status: "completed",
          completedAt: event.occurred_at,
          output: event.output,
        }),
      }

    case "stage_failed":
      if (!event.stage) return prev
      return {
        ...prev,
        isRunning: false,
        error: event.error ?? "Stage failed",
        stages: updateStage(prev.stages, event.stage, {
          status: "failed",
          completedAt: event.occurred_at,
          error: event.error,
        }),
      }

    case "duplicate_detected":
      return {
        ...prev,
        duplicate: { matchedInvoiceId: event.matched_invoice_id ?? null },
        stages: markStagesAfterDuplicate(prev.stages),
      }

    case "review_completed":
      return {
        ...prev,
        isRunning: false,
        finished: true,
      }

    case "stream_closed":
      return {
        ...prev,
        isRunning: false,
        finished: true,
      }

    case "error":
      return {
        ...prev,
        isRunning: false,
        error: event.error ?? "Stream error",
      }

    default:
      return prev
  }
}

function updateStage(
  stages: Record<StageName, StageState>,
  name: StageName,
  patch: Partial<Omit<StageState, "name">> & { status?: StageStatus }
): Record<StageName, StageState> {
  return {
    ...stages,
    [name]: {
      ...stages[name],
      ...patch,
    },
  }
}

function markStagesAfterDuplicate(
  stages: Record<StageName, StageState>
): Record<StageName, StageState> {
  const skipped: StageName[] = ["anomaly_detector", "validator", "responder"]
  const next = { ...stages }
  for (const name of skipped) {
    if (next[name].status === "queued") {
      next[name] = { ...next[name], status: "skipped" }
    }
  }
  return next
}
