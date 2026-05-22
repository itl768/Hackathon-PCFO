"use client"

import { use, useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { ArrowLeft, RotateCcw } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DocumentViewer } from "@/components/invoicing/document-viewer"
import { DuplicateNotice } from "@/components/invoicing/duplicate-notice"
import { InvoiceForm } from "@/components/invoicing/invoice-form"
import { InvoiceTimeline } from "@/components/invoicing/invoice-timeline"
import { SummaryPanel } from "@/components/invoicing/summary-panel"
import { useInvoicePipeline } from "@/hooks/use-invoice-pipeline"
import { getInvoice, getInvoiceDocumentUrl } from "@/lib/api"
import { type Invoice, type InvoiceStatus, STATUS_LABELS } from "@/lib/types"

const STATUS_VARIANT: Record<InvoiceStatus, "default" | "secondary" | "destructive" | "outline"> = {
  received: "outline",
  processing: "secondary",
  duplicate: "destructive",
  reviewed: "default",
  confirmed: "default",
  failed: "destructive",
}

export default function InvoiceEditorPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pipeline = useInvoicePipeline(id)

  const refresh = useCallback(async () => {
    try {
      const data = await getInvoice(id)
      setInvoice(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load invoice")
    }
  }, [id])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    if (pipeline.finished) {
      void refresh()
    }
  }, [pipeline.finished, refresh])

  if (error) {
    return (
      <div className="mx-auto flex min-h-svh max-w-4xl flex-col gap-4 px-4 py-10">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Back to inbox
        </Link>
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      </div>
    )
  }

  if (!invoice) {
    return (
      <div className="mx-auto flex min-h-svh max-w-4xl flex-col gap-4 px-4 py-10">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Back to inbox
        </Link>
        <div className="text-sm text-muted-foreground">Loading invoice...</div>
      </div>
    )
  }

  const isDuplicate = invoice.status === "duplicate" || !!pipeline.duplicate
  const matchedInvoiceId = invoice.duplicate_of ?? pipeline.duplicate?.matchedInvoiceId ?? null
  const documentUrl = getInvoiceDocumentUrl(invoice.invoice_id)

  return (
    <div className="flex h-svh flex-col">
      <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-4" />
            Inbox
          </Link>
          <div className="flex flex-col">
            <div className="truncate text-sm font-medium">{invoice.original_filename}</div>
            <div className="text-xs text-muted-foreground">
              Updated {new Date(invoice.updated_at).toLocaleTimeString()}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={STATUS_VARIANT[invoice.status]}>{STATUS_LABELS[invoice.status]}</Badge>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => void refresh()}
            title="Refresh"
            aria-label="Refresh invoice"
          >
            <RotateCcw className="size-4" />
          </Button>
        </div>
      </header>

      <main className="grid flex-1 min-h-0 grid-cols-1 gap-0 overflow-hidden lg:grid-cols-[1.2fr_1fr_280px]">
        <section className="min-h-0 border-b border-border lg:border-b-0 lg:border-r">
          <DocumentViewer
            documentUrl={documentUrl}
            mimeType={invoice.mime_type}
            filename={invoice.original_filename}
          />
        </section>

        <section className="min-h-0 overflow-auto border-b border-border p-5 lg:border-b-0 lg:border-r">
          {isDuplicate ? (
            <div className="flex flex-col gap-5">
              <DuplicateNotice matchedInvoiceId={matchedInvoiceId} />
              <InvoiceForm
                extraction={invoice.extraction}
                anomalies={invoice.anomalies}
                validationErrors={invoice.validation_errors}
              />
            </div>
          ) : (
            <div className="flex flex-col gap-6">
              <InvoiceForm
                extraction={invoice.extraction}
                anomalies={invoice.anomalies}
                validationErrors={invoice.validation_errors}
              />
              <SummaryPanel
                summary={invoice.summary}
                anomalies={invoice.anomalies}
                validationErrors={invoice.validation_errors}
                agentOutputs={invoice.agentOutputs}
              />
            </div>
          )}
        </section>

        <aside className="min-h-0 overflow-auto p-4">
          <InvoiceTimeline stages={pipeline.stages} duplicateMode={isDuplicate} />
          {pipeline.error && (
            <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {pipeline.error}
            </div>
          )}
        </aside>
      </main>
    </div>
  )
}
