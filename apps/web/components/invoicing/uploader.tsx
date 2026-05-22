"use client"

import { useCallback, useState } from "react"
import { FileUp, Loader2 } from "lucide-react"
import { useDropzone } from "react-dropzone"

import { uploadInvoice } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const ACCEPTED_MIMES: Record<string, string[]> = {
  "application/pdf": [".pdf"],
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
}

interface UploaderProps {
  onUploaded: (invoiceId: string) => void
}

export function Uploader({ onUploaded }: UploaderProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [forceDuplicate, setForceDuplicate] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(
    async (accepted: File[]) => {
      if (accepted.length === 0) return
      setError(null)
      setIsUploading(true)
      try {
        const file = accepted[0]
        const result = await uploadInvoice(file, { forceDuplicate })
        onUploaded(result.invoice_id)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed")
      } finally {
        setIsUploading(false)
      }
    },
    [forceDuplicate, onUploaded]
  )

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ACCEPTED_MIMES,
    multiple: false,
    disabled: isUploading,
  })

  return (
    <div className="flex flex-col gap-3">
      <div
        {...getRootProps()}
        className={cn(
          "flex h-44 cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border bg-muted/40 px-6 text-center transition-colors",
          isDragActive && !isDragReject && "border-primary bg-primary/5",
          isDragReject && "border-destructive bg-destructive/5",
          isUploading && "cursor-not-allowed opacity-60"
        )}
      >
        <input {...getInputProps()} />
        {isUploading ? (
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        ) : (
          <FileUp className="size-6 text-muted-foreground" />
        )}
        <div className="text-sm font-medium">
          {isUploading
            ? "Uploading invoice..."
            : isDragActive
              ? "Drop the invoice here"
              : "Drop an invoice or click to choose"}
        </div>
        <div className="text-xs text-muted-foreground">PDF, PNG, or JPG up to 10 MB</div>
      </div>

      <label className="flex items-center gap-2 text-xs text-muted-foreground">
        <input
          type="checkbox"
          checked={forceDuplicate}
          onChange={(event) => setForceDuplicate(event.target.checked)}
          className="size-4"
        />
        Force duplicate detection (M0 test flag)
      </label>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
          <Button
            variant="ghost"
            size="xs"
            className="ml-2"
            onClick={() => setError(null)}
          >
            dismiss
          </Button>
        </div>
      )}
    </div>
  )
}
