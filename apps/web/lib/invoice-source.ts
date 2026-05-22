import type { InvoiceSource } from "@/lib/invoice-types"

export function sourceFromFile(file: File): InvoiceSource {
  return {
    kind: "file",
    file,
    previewUrl: URL.createObjectURL(file),
    fileName: file.name,
    mimeType: file.type || "application/octet-stream",
  }
}

export function sourceFromText(text: string, label = "Pasted invoice text"): InvoiceSource {
  return { kind: "text", text, label }
}

export function revokeSourcePreview(source: InvoiceSource | null) {
  if (source?.kind === "file") {
    URL.revokeObjectURL(source.previewUrl)
  }
}
