"use client"

import { FileImage, FileText, FileType } from "lucide-react"
import { useEffect, useState } from "react"

import type { InvoiceSource } from "@/lib/invoice-types"

interface DocumentPreviewProps {
  source: InvoiceSource | null
}

function isPdf(mime: string, name: string) {
  return mime === "application/pdf" || name.toLowerCase().endsWith(".pdf")
}

function isImage(mime: string) {
  return mime.startsWith("image/")
}

export function DocumentPreview({ source }: DocumentPreviewProps) {
  if (!source) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center">
        <FileText className="mb-3 h-10 w-10 text-muted-foreground/30" />
        <p className="text-sm font-medium text-muted-foreground">Source document</p>
        <p className="mt-1 text-xs text-muted-foreground/70">
          Upload or paste an invoice to preview it here while you verify extracted data
        </p>
      </div>
    )
  }

  const header =
    source.kind === "text" ? (
      <>
        <FileText className="h-4 w-4 shrink-0 text-primary" />
        <div className="min-w-0">
          <p className="truncate text-xs font-medium">{source.label}</p>
          <p className="text-[10px] text-muted-foreground">{source.text.length} characters</p>
        </div>
      </>
    ) : isPdf(source.mimeType, source.fileName) ? (
      <>
        <FileType className="h-4 w-4 shrink-0 text-primary" />
        <div className="min-w-0">
          <p className="truncate text-xs font-medium">{source.fileName}</p>
          <p className="text-[10px] text-muted-foreground">PDF document</p>
        </div>
      </>
    ) : isImage(source.mimeType) ? (
      <>
        <FileImage className="h-4 w-4 shrink-0 text-primary" />
        <div className="min-w-0">
          <p className="truncate text-xs font-medium">{source.fileName}</p>
          <p className="text-[10px] text-muted-foreground">Image</p>
        </div>
      </>
    ) : (
      <>
        <FileText className="h-4 w-4 shrink-0 text-primary" />
        <div className="min-w-0">
          <p className="truncate text-xs font-medium">{source.fileName}</p>
          <p className="text-[10px] text-muted-foreground">{source.mimeType || "Document"}</p>
        </div>
      </>
    )

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 border-b px-4 py-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Source Document
        </h3>
        <div className="mt-2 flex items-center gap-2">{header}</div>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden bg-muted/20 p-3">
        {source.kind === "text" ? (
          <pre className="h-full overflow-auto rounded-lg border bg-background p-3 font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-foreground/90">
            {source.text}
          </pre>
        ) : source.kind === "file" && isPdf(source.mimeType, source.fileName) ? (
          <iframe
            title={source.fileName}
            src={`${source.previewUrl}#toolbar=0&navpanes=0`}
            className="h-full w-full rounded-lg border bg-background"
          />
        ) : source.kind === "file" && isImage(source.mimeType) ? (
          <div className="flex h-full items-start justify-center overflow-auto">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={source.previewUrl}
              alt={source.fileName}
              className="max-h-full max-w-full rounded-lg border bg-background object-contain shadow-sm"
            />
          </div>
        ) : source.kind === "file" ? (
          <TextFilePreview file={source.file} />
        ) : null}
      </div>
    </div>
  )
}

function TextFilePreview({ file }: { file: File }) {
  const [content, setContent] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    file.text().then((t) => {
      if (!cancelled) setContent(t)
    })
    return () => {
      cancelled = true
    }
  }, [file])

  if (content === null) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border bg-background text-xs text-muted-foreground">
        Loading preview...
      </div>
    )
  }

  return (
    <pre className="h-full overflow-auto rounded-lg border bg-background p-3 font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
      {content}
    </pre>
  )
}
