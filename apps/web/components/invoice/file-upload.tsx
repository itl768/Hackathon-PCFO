"use client"

import { Upload, FileText, Sparkles } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"

import type { SampleInvoice } from "@/lib/invoice-types"
import { shortenFileName } from "@/lib/utils"

interface FileUploadProps {
  samples: SampleInvoice[]
  onProcess: (payload: { file?: File; text?: string }) => void
  isProcessing: boolean
  clearUploadKey?: number
}

export function FileUpload({
  samples,
  onProcess,
  isProcessing,
  clearUploadKey = 0,
}: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [pastedText, setPastedText] = useState("")
  const [mode, setMode] = useState<"upload" | "paste">("upload")
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setSelectedFile(null)
    setPastedText("")
    setMode("upload")
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }, [clearUploadKey])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      setSelectedFile(file)
      setMode("upload")
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      setMode("upload")
    }
  }, [])

  const handleSampleSelect = useCallback(
    (sampleId: string) => {
      const sample = samples.find((s) => s.id === sampleId)
      if (sample) {
        setPastedText(sample.text)
        setSelectedFile(null)
        setMode("paste")
      }
    },
    [samples],
  )

  const handleProcess = () => {
    if (mode === "upload" && selectedFile) {
      onProcess({ file: selectedFile })
    } else if (mode === "paste" && pastedText.trim()) {
      onProcess({ text: pastedText })
    }
  }

  const canProcess = (mode === "upload" && selectedFile) || (mode === "paste" && pastedText.trim())

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Invoice Input
      </h3>

      <div className="flex rounded-lg border bg-muted/30 p-0.5">
        <button
          onClick={() => setMode("upload")}
          className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
            mode === "upload" ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Upload File
        </button>
        <button
          onClick={() => setMode("paste")}
          className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
            mode === "paste" ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Paste Text
        </button>
      </div>

      {mode === "upload" ? (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onClick={() => fileInputRef.current?.click()}
          className={`flex min-h-[140px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed transition-all ${
            dragOver
              ? "border-primary bg-primary/5"
              : selectedFile
                ? "border-green-500/50 bg-green-500/5"
                : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/30"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.csv"
            onChange={handleFileSelect}
          />
          {selectedFile ? (
            <>
              <FileText className="mb-2 h-8 w-8 text-green-500" />
              <p
                className="max-w-full truncate px-2 text-sm font-medium"
                title={selectedFile.name}
              >
                {shortenFileName(selectedFile.name)}
              </p>
              <p className="text-xs text-muted-foreground">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
            </>
          ) : (
            <>
              <Upload className="mb-2 h-8 w-8 text-muted-foreground/50" />
              <p className="text-sm font-medium text-muted-foreground">
                Drop invoice here
              </p>
              <p className="text-xs text-muted-foreground/70">PDF, Image, or Text</p>
            </>
          )}
        </div>
      ) : (
        <textarea
          value={pastedText}
          onChange={(e) => setPastedText(e.target.value)}
          placeholder="Paste invoice text here..."
          className="min-h-[140px] resize-none rounded-xl border bg-muted/20 p-3 text-sm focus:border-primary focus:outline-none"
        />
      )}

      {samples.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-medium text-muted-foreground">Try a sample:</p>
          <div className="flex flex-col gap-1.5">
            {samples.map((sample) => (
              <button
                key={sample.id}
                onClick={() => handleSampleSelect(sample.id)}
                className="flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs transition-all hover:border-primary/50 hover:bg-muted/30"
              >
                <Sparkles className="h-3.5 w-3.5 shrink-0 text-primary" />
                <div>
                  <p className="font-medium">{sample.name}</p>
                  <p className="text-muted-foreground">{sample.description}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={handleProcess}
        disabled={!canProcess || isProcessing}
        className={`mt-auto flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold transition-all ${
          canProcess && !isProcessing
            ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25 hover:shadow-primary/40"
            : "cursor-not-allowed bg-muted text-muted-foreground"
        }`}
      >
        {isProcessing ? (
          <>
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            Processing...
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" />
            Process Invoice
          </>
        )}
      </button>
    </div>
  )
}
