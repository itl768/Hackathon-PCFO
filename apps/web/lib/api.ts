import { createParser } from "eventsource-parser"

import {
  API_URL,
  type Invoice,
  type InvoiceListItem,
  type StageEvent,
  type StageEventType,
  type UploadResponse,
} from "@/lib/types"

export async function uploadInvoice(
  file: File,
  options?: { forceDuplicate?: boolean }
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append("file", file)

  const url = new URL(`${API_URL}/api/invoices`)
  if (options?.forceDuplicate) {
    url.searchParams.set("force_duplicate", "true")
  }

  const response = await fetch(url.toString(), {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`Upload failed: ${response.status} ${detail}`)
  }
  return (await response.json()) as UploadResponse
}

export async function listInvoices(): Promise<InvoiceListItem[]> {
  const response = await fetch(`${API_URL}/api/invoices`, { cache: "no-store" })
  if (!response.ok) {
    throw new Error(`Failed to list invoices: ${response.status}`)
  }
  return (await response.json()) as InvoiceListItem[]
}

export async function getInvoice(invoiceId: string): Promise<Invoice> {
  const response = await fetch(`${API_URL}/api/invoices/${invoiceId}`, { cache: "no-store" })
  if (!response.ok) {
    throw new Error(`Failed to load invoice ${invoiceId}: ${response.status}`)
  }
  return (await response.json()) as Invoice
}

export function getInvoiceDocumentUrl(invoiceId: string): string {
  return `${API_URL}/api/invoices/${invoiceId}/document`
}

export async function* subscribeToInvoiceEvents(
  invoiceId: string,
  signal?: AbortSignal
): AsyncGenerator<StageEvent, void, unknown> {
  const response = await fetch(`${API_URL}/api/invoices/${invoiceId}/events`, {
    signal,
    headers: { Accept: "text/event-stream" },
  })

  if (!response.ok) {
    throw new Error(`Event stream failed: ${response.status}`)
  }
  if (!response.body) {
    throw new Error("Event stream body is null")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  const buffer: StageEvent[] = []
  let resolveNext: ((value: IteratorResult<StageEvent>) => void) | null = null
  let done = false

  const push = (event: StageEvent) => {
    if (resolveNext) {
      const resolve = resolveNext
      resolveNext = null
      resolve({ value: event, done: false })
    } else {
      buffer.push(event)
    }
  }

  const finish = () => {
    done = true
    if (resolveNext) {
      const resolve = resolveNext
      resolveNext = null
      resolve({ value: undefined as unknown as StageEvent, done: true })
    }
  }

  const parser = createParser({
    onEvent(event) {
      try {
        const data = event.data ? JSON.parse(event.data) : {}
        push({
          type: (event.event ?? "stage_started") as StageEventType,
          ...data,
        } as StageEvent)
      } catch {
        /* ignore malformed payloads */
      }
    },
  })

  const reading = (async () => {
    try {
      for (;;) {
        const { value, done: streamDone } = await reader.read()
        if (streamDone) break
        parser.feed(decoder.decode(value, { stream: true }))
      }
    } finally {
      finish()
    }
  })()

  try {
    for (;;) {
      if (buffer.length > 0) {
        yield buffer.shift()!
      } else if (done) {
        break
      } else {
        const result = await new Promise<IteratorResult<StageEvent>>((resolve) => {
          resolveNext = resolve
        })
        if (result.done) break
        yield result.value
      }
    }
  } finally {
    await reading.catch(() => undefined)
  }
}
