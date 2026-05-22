"use client"

import { FileText, MessageSquare, History, RotateCcw, Pencil } from "lucide-react"
import { ThemeToggle } from "@/components/theme-toggle"
import { useCallback, useEffect, useRef, useState } from "react"

import { AgentLog } from "@/components/invoice/agent-log"
import { DocumentPreview } from "@/components/invoice/document-preview"
import { FileUpload } from "@/components/invoice/file-upload"
import { InvoiceChat } from "@/components/invoice/invoice-chat"
import { PipelineVisualizer } from "@/components/invoice/pipeline-visualizer"
import { InvoiceEditDrawer } from "@/components/invoice/invoice-edit-drawer"
import { ResultsPanel } from "@/components/invoice/results-panel"
import { fetchHistory, fetchSamples, streamProcessInvoice } from "@/lib/invoice-api"
import { revokeSourcePreview } from "@/lib/invoice-source"
import type {
  AgentLogEntry,
  HistoryEntry,
  InvoiceSource,
  PipelineStep,
  PipelineStepState,
  ProcessingReport,
  SampleInvoice,
} from "@/lib/invoice-types"

type Tab = "process" | "chat" | "history"

const INITIAL_STEPS: PipelineStepState[] = [
  { id: "doc_reader", label: "Document Reader", status: "idle" },
  { id: "dedup_file", label: "DeDup · File Hash", status: "idle" },
  { id: "extract", label: "Extractor", status: "idle" },
  { id: "dedup_exact", label: "DeDup · History", status: "idle" },
  { id: "validate", label: "Validator", status: "idle" },
  { id: "anomaly_detect", label: "Anomaly Detector", status: "idle" },
  { id: "embed", label: "Embeddings · pgvector", status: "idle" },
  { id: "respond", label: "Responder", status: "idle" },
]

export default function InvoicePage() {
  const [tab, setTab] = useState<Tab>("process")
  const [samples, setSamples] = useState<SampleInvoice[]>([])
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [steps, setSteps] = useState<PipelineStepState[]>(INITIAL_STEPS)
  const [report, setReport] = useState<ProcessingReport | null>(null)
  const [agentLog, setAgentLog] = useState<AgentLogEntry[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [activeStepId, setActiveStepId] = useState<string | null>(null)
  const [source, setSource] = useState<InvoiceSource | null>(null)
  const sourceRef = useRef<InvoiceSource | null>(null)
  sourceRef.current = source
  const [editInvoiceId, setEditInvoiceId] = useState<number | null>(null)
  const [clearUploadKey, setClearUploadKey] = useState(0)
  useEffect(() => {
    fetchSamples().then(setSamples).catch(console.error)
  }, [])

  useEffect(() => {
    if (tab === "history") {
      fetchHistory().then(setHistory).catch(console.error)
    }
  }, [tab])

  const updateStep = useCallback((id: string, update: Partial<PipelineStepState>) => {
    setSteps((prev) =>
      prev.map((s) => (s.id === id ? { ...s, ...update } : s)),
    )
  }, [])

  const handleReset = useCallback(() => {
    setSteps(INITIAL_STEPS)
    setReport(null)
    setAgentLog([])
    setActiveStepId(null)
    setSource((prev) => {
      revokeSourcePreview(prev)
      return null
    })
  }, [])

  const handleSourceChange = useCallback((next: InvoiceSource | null) => {
    setSource((prev) => {
      if (prev?.kind === "file" && next?.kind === "file" && prev.previewUrl !== next.previewUrl) {
        URL.revokeObjectURL(prev.previewUrl)
      } else if (prev?.kind === "file" && (next === null || next.kind === "text")) {
        revokeSourcePreview(prev)
      }
      return next
    })
  }, [])

  useEffect(() => {
    return () => revokeSourcePreview(sourceRef.current)
  }, [])

  const handleProcess = useCallback(
    async (payload: { file?: File; text?: string }) => {
      setSteps(INITIAL_STEPS)
      setReport(null)
      setAgentLog([])
      setActiveStepId(null)
      setIsProcessing(true)

      let completed = false

      try {
        for await (const evt of streamProcessInvoice(payload)) {
          const data = evt.data as Record<string, unknown>

          switch (evt.event) {
            case "step_start": {
              const agent = data.agent as PipelineStep
              setActiveStepId(agent)
              updateStep(agent, { status: "running", message: data.message as string })
              break
            }

            case "step_skip": {
              const agent = data.agent as PipelineStep
              updateStep(agent, {
                status: "skipped",
                message: (data.message as string) || "Skipped",
              })
              break
            }

            case "step_complete": {
              const agent = data.agent as PipelineStep
              const status = data.status as string
              updateStep(agent, {
                status: status === "error" ? "error" : status === "warning" ? "warning" : "success",
                message: data.message as string,
              })
              break
            }

            case "agent_log": {
              const entry = data as unknown as AgentLogEntry
              setAgentLog((prev) => [...prev, entry])
              break
            }

            case "final_report": {
              setReport(data as unknown as ProcessingReport)
              completed = true
              break
            }

            case "error": {
              console.error("Pipeline error:", data.detail)
              break
            }
          }
        }
      } catch (err) {
        console.error("Process error:", err)
      } finally {
        if (completed) {
          setClearUploadKey((k) => k + 1)
        }
        setIsProcessing(false)
        setActiveStepId(null)
      }
    },
    [updateStep],
  )

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header */}
      <header className="flex items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <FileText className="h-4 w-4 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-sm font-bold">Invoice Processing</h1>
            <p className="text-[10px] text-muted-foreground">
              Multi-Agent Workflow
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1 rounded-lg border bg-muted/30 p-0.5">
          <TabButton
            active={tab === "process"}
            onClick={() => setTab("process")}
            icon={FileText}
            label="Process"
          />
          <TabButton
            active={tab === "chat"}
            onClick={() => setTab("chat")}
            icon={MessageSquare}
            label="Chat"
          />
          <TabButton
            active={tab === "history"}
            onClick={() => setTab("history")}
            icon={History}
            label="History"
          />
        </div>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          {tab === "process" && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-all hover:bg-muted hover:text-foreground"
            >
              <RotateCcw className="h-3 w-3" />
              Reset
            </button>
          )}
        </div>
      </header>

      {/* Content */}
      {tab === "process" && (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex min-h-0 flex-1">
            {/* Left: Input */}
            <div className="w-72 shrink-0 border-r">
              <FileUpload
                samples={samples}
                onProcess={handleProcess}
                onSourceChange={handleSourceChange}
                isProcessing={isProcessing}
                clearUploadKey={clearUploadKey}
              />
            </div>

            {/* Center: Pipeline */}
            <div className="flex min-w-0 flex-1 items-center justify-center overflow-y-auto border-r">
              <PipelineVisualizer
                steps={steps}
                activeStepId={activeStepId}
                isProcessing={isProcessing}
              />
            </div>

            {/* Right: Results + source document */}
            <div className="flex w-[min(1120px,56vw)] min-w-[42rem] shrink-0 border-l">
              <div className="w-[28rem] min-w-[24rem] shrink-0 overflow-y-auto border-r">
                <ResultsPanel report={report} />
              </div>
              <div className="min-w-[14rem] flex-1">
                <DocumentPreview source={source} />
              </div>
            </div>
          </div>

          {/* Bottom: Agent Log */}
          <AgentLog entries={agentLog} />
        </div>
      )}

      {tab === "chat" && (
        <div className="min-h-0 flex-1">
          <InvoiceChat />
        </div>
      )}

      {tab === "history" && (
        <div className="relative min-h-0 flex-1 overflow-y-auto p-6">
          <HistoryTable
            entries={history}
            onEdit={(id) => setEditInvoiceId(id)}
          />
          <InvoiceEditDrawer
            invoiceId={editInvoiceId}
            onClose={() => setEditInvoiceId(null)}
            onSaved={() => fetchHistory().then(setHistory).catch(console.error)}
          />
        </div>
      )}
    </div>
  )
}

function TabButton({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean
  onClick: () => void
  icon: React.ComponentType<{ className?: string }>
  label: string
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
        active ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
      }`}
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </button>
  )
}

function HistoryTable({
  entries,
  onEdit,
}: {
  entries: HistoryEntry[]
  onEdit: (id: number) => void
}) {
  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <History className="mb-3 h-10 w-10 text-muted-foreground/30" />
        <p className="text-sm text-muted-foreground">No invoices processed yet</p>
      </div>
    )
  }

  const statusColor = (s: string) =>
    s.includes("Approve") && !s.includes("Reject")
      ? "bg-emerald-500/10 text-emerald-700 border-emerald-500/30"
      : s.includes("Reject")
        ? "bg-red-500/10 text-red-700 border-red-500/30"
        : "bg-amber-500/10 text-amber-700 border-amber-500/30"

  return (
    <div className="overflow-x-auto rounded-xl border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/30">
            <th className="px-4 py-3 text-left font-medium">Invoice #</th>
            <th className="px-4 py-3 text-left font-medium">Vendor</th>
            <th className="px-4 py-3 text-right font-medium">Amount</th>
            <th className="px-4 py-3 text-center font-medium">Risk</th>
            <th className="px-4 py-3 text-center font-medium">Status</th>
            <th className="px-4 py-3 text-right font-medium">Processed</th>
            <th className="px-4 py-3 text-center font-medium w-16" />
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr
              key={e.id}
              className="cursor-pointer border-b last:border-0 hover:bg-muted/10"
              onClick={() => onEdit(e.id)}
            >
              <td className="px-4 py-3 font-mono text-xs">{e.invoice_number || "—"}</td>
              <td className="px-4 py-3">{e.vendor_name || "—"}</td>
              <td className="px-4 py-3 text-right font-mono">
                {e.currency} {e.total_amount?.toFixed(2) ?? "—"}
              </td>
              <td className="px-4 py-3 text-center">
                <span className="font-mono text-xs font-bold">{e.risk_score ?? "—"}</span>
              </td>
              <td className="px-4 py-3 text-center">
                <span
                  className={`inline-flex rounded-md border px-2 py-0.5 text-[10px] font-bold ${statusColor(e.status)}`}
                >
                  {e.status}
                </span>
              </td>
              <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                {e.processed_at ? new Date(e.processed_at).toLocaleString() : "—"}
              </td>
              <td className="px-4 py-3 text-center">
                <button
                  type="button"
                  onClick={(ev) => {
                    ev.stopPropagation()
                    onEdit(e.id)
                  }}
                  className="inline-flex rounded-md border p-1.5 text-muted-foreground transition-colors hover:border-primary/50 hover:bg-primary/5 hover:text-primary"
                  title="Edit invoice"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
