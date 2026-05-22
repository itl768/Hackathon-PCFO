export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export type InvoiceStatus =
  | "received"
  | "processing"
  | "duplicate"
  | "reviewed"
  | "confirmed"
  | "failed"

export const STAGE_NAMES = [
  "extractor",
  "deduplication",
  "anomaly_detector",
  "validator",
  "responder",
  "duplicate_handler",
] as const

export type StageName = (typeof STAGE_NAMES)[number]

export type StageStatus = "queued" | "running" | "completed" | "failed" | "skipped"

export interface StageState {
  name: StageName
  status: StageStatus
  startedAt?: string
  completedAt?: string
  output?: Record<string, unknown>
  error?: string
}

export interface LineItem {
  name: string
  quantity: number
  unit_price: number
  total: number
}

export interface ExtractionFields {
  invoice_number: string | null
  vendor_name: string | null
  invoice_date: string | null
  due_date: string | null
  line_items: LineItem[]
  total_amount: number | null
  tax_amount: number | null
  currency: string
}

export interface Finding {
  field_path: string
  message: string
  severity: "low" | "medium" | "high"
  source_agent: string
}

export type Anomaly = Finding
export type ValidationError = Finding

export interface ReviewSummary {
  verdict: "good" | "needs_review"
  text: string
  anomaly_count: number
  validation_error_count: number
}

export interface Invoice {
  invoice_id: string
  status: InvoiceStatus
  original_filename: string
  mime_type: string
  document_url: string
  extraction: ExtractionFields | null
  summary: ReviewSummary | null
  agentOutputs: Record<string, Record<string, unknown>>
  anomalies: Anomaly[]
  validation_errors: ValidationError[]
  duplicate_of: string | null
  failure_reason: string | null
  created_at: string
  updated_at: string
}

export interface InvoiceListItem {
  invoice_id: string
  status: InvoiceStatus
  original_filename: string
  vendor_name: string | null
  invoice_number: string | null
  invoice_date: string | null
  total_amount: number | null
  currency: string | null
  duplicate_of: string | null
  created_at: string
}

export interface UploadResponse {
  invoice_id: string
  status: InvoiceStatus
}

export type StageEventType =
  | "invoice_received"
  | "stage_started"
  | "stage_completed"
  | "stage_failed"
  | "duplicate_detected"
  | "review_completed"
  | "stream_closed"
  | "error"

export interface StageEvent {
  type: StageEventType
  invoice_id: string
  stage?: StageName
  output?: Record<string, unknown>
  error?: string
  occurred_at?: string
  matched_invoice_id?: string | null
  verdict?: string
}

export const STAGE_LABELS: Record<StageName, string> = {
  extractor: "Extractor",
  deduplication: "Deduplication",
  anomaly_detector: "Anomaly Detector",
  validator: "Validator",
  responder: "Responder",
  duplicate_handler: "Duplicate Handler",
}

export const STATUS_LABELS: Record<InvoiceStatus, string> = {
  received: "Received",
  processing: "Processing",
  duplicate: "Duplicate",
  reviewed: "Reviewed",
  confirmed: "Confirmed",
  failed: "Failed",
}
