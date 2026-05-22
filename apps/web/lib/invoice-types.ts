export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface LineItem {
  description: string
  quantity: number
  unit_price: number
  net_amount: number
  vat_amount: number
  line_total: number
}

export interface ExtractedInvoice {
  vendor_name: string | null
  invoice_number: string | null
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
  dedup_vector: DuplicationResult | null
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
  | "dedup_vector"
  | "extract"
  | "dedup_exact"
  | "validate"
  | "anomaly_detect"
  | "respond"

export type StepStatus = "idle" | "running" | "success" | "warning" | "error"

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
