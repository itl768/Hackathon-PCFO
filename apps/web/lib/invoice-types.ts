export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface LineItem {
  id?: number | null
  gl_account: string | null
  description: string
  quantity: number
  unit_price: number
  net_amount: number
  vat_rate: number | null
  vat_amount: number
  line_total: number
}

export interface ExtractedInvoice {
  vendor_name: string | null
  vendor_iban: string | null
  vendor_vat_number: string | null
  vendor_country: string | null
  vat_reversed: boolean
  invoice_number: string | null
  payment_reference: string | null
  invoice_date: string | null
  due_date: string | null
  line_items: LineItem[]
  subtotal: number | null
  vat_total: number | null
  total_amount: number | null
  currency: string
  payment_terms: string | null
}

export interface DuplicationResult {
  is_duplicate: boolean
  similarity_score: number
  matched_invoice_id: number | null
  matched_invoice_number: string | null
  method: string
}

export interface ValidationRule {
  rule_name: string
  passed: boolean
  message: string
}

export interface AnomalyFlag {
  flag_type: string
  severity: string
  description: string
}

export interface ValidationResult {
  rules: ValidationRule[]
  all_passed: boolean
  failed_count: number
}

export interface AnomalyResult {
  flags: AnomalyFlag[]
  risk_score: number
  risk_level: string
}

export interface AgentLogEntry {
  timestamp: string
  agent_name: string
  message: string
  status: string
  data?: Record<string, unknown>
}

export interface ProcessingReport {
  summary: string
  agent_outputs: Record<string, unknown>
  decision: string
  recommendation: string
  confidence: string
  risk_score: number
  next_steps: string[]
  extracted_invoice: ExtractedInvoice | null
  dedup_file: DuplicationResult | null
  dedup_exact: DuplicationResult | null
  validation: ValidationResult | null
  anomalies: AnomalyResult | null
}

export interface SampleInvoice {
  id: string
  name: string
  description: string
  text: string
}

export type PipelineStep =
  | "doc_reader"
  | "dedup_file"
  | "extract"
  | "dedup_exact"
  | "validate"
  | "anomaly_detect"
  | "embed"
  | "respond"

export type StepStatus = "idle" | "running" | "success" | "warning" | "error" | "skipped"

export interface PipelineStepState {
  id: PipelineStep
  label: string
  status: StepStatus
  message?: string
}

export interface SSEEvent {
  event: string
  data: string
}

export interface HistoryEntry {
  id: number
  invoice_number: string | null
  vendor_name: string | null
  total_amount: number | null
  status: string
  risk_score: number | null
  currency: string | null
  invoice_date: string | null
  processed_at: string | null
}

export interface InvoiceHistoryDetail {
  id: number
  invoice_number: string | null
  payment_reference: string | null
  vendor_name: string | null
  vendor_iban: string | null
  vendor_vat_number: string | null
  vendor_country: string | null
  vat_reversed: boolean
  invoice_date: string | null
  due_date: string | null
  subtotal: number | null
  vat_total: number | null
  total_amount: number | null
  currency: string
  payment_terms: string | null
  status: string
  risk_score: number | null
  file_name: string | null
  processed_at: string | null
  source_text: string | null
  line_items: LineItem[]
}

export interface InvoiceHistoryUpdate {
  invoice_number: string | null
  payment_reference: string | null
  vendor_name: string | null
  vendor_iban: string | null
  vendor_vat_number: string | null
  vendor_country: string | null
  vat_reversed: boolean
  invoice_date: string | null
  due_date: string | null
  subtotal: number | null
  vat_total: number | null
  total_amount: number | null
  currency: string
  payment_terms: string | null
  line_items: LineItem[]
}

export type InvoiceSource =
  | {
      kind: "file"
      file: File
      previewUrl: string
      fileName: string
      mimeType: string
    }
  | {
      kind: "text"
      text: string
      label: string
    }
