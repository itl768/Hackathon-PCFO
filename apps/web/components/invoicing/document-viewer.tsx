"use client"

import { useEffect, useState } from "react"
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react"
import { Document, Page, pdfjs } from "react-pdf"

import "react-pdf/dist/Page/AnnotationLayer.css"
import "react-pdf/dist/Page/TextLayer.css"

import { Button } from "@/components/ui/button"

if (typeof window !== "undefined") {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`
}

interface DocumentViewerProps {
  documentUrl: string
  mimeType: string
  filename: string
}

export function DocumentViewer({ documentUrl, mimeType, filename }: DocumentViewerProps) {
  if (mimeType === "application/pdf") {
    return <PdfViewer url={documentUrl} />
  }
  return <ImageViewer url={documentUrl} alt={filename} />
}

function ImageViewer({ url, alt }: { url: string; alt: string }) {
  return (
    <div className="flex h-full items-center justify-center overflow-auto bg-muted/40 p-4">
      <img src={url} alt={alt} className="max-h-full max-w-full rounded-md shadow-sm" />
    </div>
  )
}

function PdfViewer({ url }: { url: string }) {
  const [numPages, setNumPages] = useState<number | null>(null)
  const [pageNumber, setPageNumber] = useState(1)
  const [containerWidth, setContainerWidth] = useState<number | null>(null)

  useEffect(() => {
    const resize = () => {
      const el = document.getElementById("pdf-viewer-container")
      if (el) {
        setContainerWidth(el.clientWidth - 24)
      }
    }
    resize()
    window.addEventListener("resize", resize)
    return () => window.removeEventListener("resize", resize)
  }, [])

  return (
    <div
      id="pdf-viewer-container"
      className="flex h-full flex-col items-center overflow-auto bg-muted/40 p-3"
    >
      <Document
        file={url}
        onLoadSuccess={({ numPages: total }) => setNumPages(total)}
        loading={
          <div className="flex h-full items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" /> Loading document...
          </div>
        }
        error={
          <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            Failed to render PDF
          </div>
        }
      >
        <Page
          pageNumber={pageNumber}
          width={containerWidth ?? undefined}
          renderAnnotationLayer={false}
          renderTextLayer={false}
          className="rounded-md shadow-sm"
        />
      </Document>

      {numPages && numPages > 1 && (
        <div className="mt-3 flex items-center gap-2">
          <Button
            variant="outline"
            size="icon-sm"
            disabled={pageNumber <= 1}
            onClick={() => setPageNumber((p) => Math.max(1, p - 1))}
            aria-label="Previous page"
          >
            <ChevronLeft className="size-4" />
          </Button>
          <span className="text-xs text-muted-foreground">
            Page {pageNumber} of {numPages}
          </span>
          <Button
            variant="outline"
            size="icon-sm"
            disabled={pageNumber >= numPages}
            onClick={() => setPageNumber((p) => Math.min(numPages, p + 1))}
            aria-label="Next page"
          >
            <ChevronRight className="size-4" />
          </Button>
        </div>
      )}
    </div>
  )
}
