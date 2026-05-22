import { createParser } from "eventsource-parser"

import type {
  HistoryEntry,
  InvoiceHistoryDetail,
  InvoiceHistoryUpdate,
  LineItem,
  SampleInvoice,
} from "@/lib/invoice-types"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface InvoiceSettings {
  default_currency: string
  supported_currencies: string[]
  approval_threshold: number
}

export async function fetchInvoiceSettings(): Promise<InvoiceSettings> {
  const res = await fetch(`${API_URL}/api/invoice/settings`)
  if (!res.ok) throw new Error("Failed to fetch invoice settings")
  return res.json()
}

export async function fetchSamples(): Promise<SampleInvoice[]> {
  const res = await fetch(`${API_URL}/api/invoice/samples`)
  if (!res.ok) throw new Error("Failed to fetch samples")
  return res.json()
}

export async function fetchHistory(): Promise<HistoryEntry[]> {
  const res = await fetch(`${API_URL}/api/invoice/history`)
  if (!res.ok) throw new Error("Failed to fetch history")
  return res.json()
}

export async function fetchHistoryInvoice(id: number): Promise<InvoiceHistoryDetail> {
  const res = await fetch(`${API_URL}/api/invoice/history/${id}`)
  if (!res.ok) throw new Error("Failed to fetch invoice")
  return res.json()
}

export async function updateHistoryInvoice(
  id: number,
  body: InvoiceHistoryUpdate,
): Promise<InvoiceHistoryDetail> {
  const res = await fetch(`${API_URL}/api/invoice/history/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error("Failed to update invoice")
  return res.json()
}

export function emptyLineItem(): LineItem {
  return {
    gl_account: null,
    description: "",
    quantity: 1,
    unit_price: 0,
    net_amount: 0,
    vat_rate: 0,
    vat_amount: 0,
    line_total: 0,
  }
}

export interface InvoiceSSEEvent {
  event: string
  data: Record<string, unknown>
}

export async function* streamProcessInvoice(
  payload: { file?: File; text?: string },
): AsyncGenerator<InvoiceSSEEvent, void, unknown> {
  const formData = new FormData()
  if (payload.file) {
    formData.append("file", payload.file)
  } else if (payload.text) {
    formData.append("text", payload.text)
  }

  const response = await fetch(`${API_URL}/api/invoice/process`, {
    method: "POST",
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }

  if (!response.body) throw new Error("Response body is null")

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  const buffer: InvoiceSSEEvent[] = []
  let resolveNext: ((value: IteratorResult<InvoiceSSEEvent>) => void) | null = null
  let streamDone = false

  function push(evt: InvoiceSSEEvent) {
    if (resolveNext) {
      const r = resolveNext
      resolveNext = null
      r({ value: evt, done: false })
    } else {
      buffer.push(evt)
    }
  }

  function finish() {
    streamDone = true
    if (resolveNext) {
      const r = resolveNext
      resolveNext = null
      r({ value: undefined as unknown as InvoiceSSEEvent, done: true })
    }
  }

  const parser = createParser({
    onEvent(event) {
      try {
        push({ event: event.event ?? "message", data: JSON.parse(event.data) })
      } catch {
        /* skip */
      }
    },
  })

  const reading = (async () => {
    try {
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        parser.feed(decoder.decode(value, { stream: true }))
      }
    } finally {
      finish()
    }
  })()

  for (;;) {
    if (buffer.length > 0) {
      yield buffer.shift()!
    } else if (streamDone) {
      break
    } else {
      const result = await new Promise<IteratorResult<InvoiceSSEEvent>>((resolve) => {
        resolveNext = resolve
      })
      if (result.done) break
      yield result.value
    }
  }

  await reading
}

export async function* streamChat(message: string): AsyncGenerator<string, void, unknown> {
  const response = await fetch(`${API_URL}/api/invoice/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  })

  if (!response.ok) throw new Error(`API error: ${response.status}`)
  if (!response.body) throw new Error("No body")

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  const tokenBuffer: string[] = []
  let resolveNext: ((value: IteratorResult<string>) => void) | null = null
  let done = false

  function finish() {
    done = true
    if (resolveNext) {
      const r = resolveNext
      resolveNext = null
      r({ value: undefined as unknown as string, done: true })
    }
  }

  const liveParser = createParser({
    onEvent(event) {
      try {
        const data = JSON.parse(event.data)
        if (data.token) {
          if (resolveNext) {
            const r = resolveNext
            resolveNext = null
            r({ value: data.token, done: false })
          } else {
            tokenBuffer.push(data.token)
          }
        }
      } catch {
        /* skip */
      }
    },
  })

  const reading = (async () => {
    try {
      for (;;) {
        const { value, done: d } = await reader.read()
        if (d) break
        liveParser.feed(decoder.decode(value, { stream: true }))
      }
    } finally {
      finish()
    }
  })()

  for (;;) {
    if (tokenBuffer.length > 0) {
      yield tokenBuffer.shift()!
    } else if (done) {
      break
    } else {
      const result = await new Promise<IteratorResult<string>>((resolve) => {
        resolveNext = resolve
      })
      if (result.done) break
      yield result.value
    }
  }

  await reading
}
