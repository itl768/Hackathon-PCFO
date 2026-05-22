import type { AnomalyFlag, ExtractedInvoice, ProcessingReport, ValidationRule } from "@/lib/invoice-types"

export type AlertSource = "validation" | "anomaly"
export type AlertSeverity = "high" | "medium" | "low"

export interface FieldAlert {
  sources: AlertSource[]
  severity: AlertSeverity
  messages: string[]
}

export type FieldAlerts = Record<string, FieldAlert>

export interface TabNotifications {
  extracted: boolean
  validation: boolean
  anomalies: boolean
  report: boolean
}

const SEVERITY_RANK: Record<AlertSeverity, number> = { low: 0, medium: 1, high: 2 }

function parseLineIndex(text: string): number | null {
  const m = text.match(/Line\s+(\d+)/i)
  if (!m) return null
  const n = parseInt(m[1], 10)
  return Number.isFinite(n) && n > 0 ? n - 1 : null
}

function bumpSeverity(current: AlertSeverity, next: AlertSeverity): AlertSeverity {
  return SEVERITY_RANK[next] > SEVERITY_RANK[current] ? next : current
}

function addAlert(
  alerts: FieldAlerts,
  key: string,
  source: AlertSource,
  severity: AlertSeverity,
  message: string,
) {
  const existing = alerts[key]
  if (existing) {
    existing.sources = [...new Set([...existing.sources, source])]
    existing.severity = bumpSeverity(existing.severity, severity)
    if (!existing.messages.includes(message)) existing.messages.push(message)
    return
  }
  alerts[key] = { sources: [source], severity, messages: [message] }
}

function mapValidationRule(alerts: FieldAlerts, rule: ValidationRule) {
  if (rule.passed) return
  const msg = rule.message
  const name = rule.rule_name
  const sev: AlertSeverity = "high"

  const lineIdx = parseLineIndex(msg)

  switch (name) {
    case "Line Item Totals Match Bill Total":
      addAlert(alerts, "total_amount", "validation", sev, msg)
      break
    case "VAT Totals Match Line Item VAT":
      addAlert(alerts, "vat_total", "validation", sev, msg)
      break
    case "VAT Below Total Amount":
      addAlert(alerts, "vat_total", "validation", sev, msg)
      addAlert(alerts, "total_amount", "validation", sev, msg)
      break
    case "Net + VAT = Line Total (per item)":
      if (lineIdx !== null) addAlert(alerts, `line:${lineIdx}`, "validation", sev, msg)
      else {
        for (const m of msg.matchAll(/Line\s+(\d+)/gi)) {
          const idx = parseInt(m[1], 10) - 1
          if (idx >= 0) addAlert(alerts, `line:${idx}`, "validation", sev, msg)
        }
      }
      break
    case "Required Fields Present":
      if (/vendor/i.test(msg)) addAlert(alerts, "vendor_name", "validation", sev, msg)
      if (/total amount/i.test(msg)) addAlert(alerts, "total_amount", "validation", sev, msg)
      if (/invoice date/i.test(msg)) addAlert(alerts, "invoice_date", "validation", sev, msg)
      break
    case "Invoice Number Present":
      addAlert(alerts, "invoice_number", "validation", sev, msg)
      break
    case "Invoice Date In Allowed Range":
      addAlert(alerts, "invoice_date", "validation", sev, msg)
      break
    case "Due Date Not Before Invoice Date":
      addAlert(alerts, "due_date", "validation", sev, msg)
      addAlert(alerts, "invoice_date", "validation", sev, msg)
      break
    case "Subtotal + VAT = Total Amount":
      addAlert(alerts, "subtotal", "validation", sev, msg)
      addAlert(alerts, "vat_total", "validation", sev, msg)
      addAlert(alerts, "total_amount", "validation", sev, msg)
      break
    case "Line Net Not Exceed Line Total":
      if (lineIdx !== null) addAlert(alerts, `line:${lineIdx}`, "validation", sev, msg)
      break
    case "Quantity × Unit Price ≈ Net (per line)":
      if (lineIdx !== null) addAlert(alerts, `line:${lineIdx}`, "validation", sev, msg)
      break
    case "Line Items Have Description":
      if (lineIdx !== null) addAlert(alerts, `line:${lineIdx}`, "validation", sev, msg)
      break
    case "Total Amount Is Positive":
      addAlert(alerts, "total_amount", "validation", sev, msg)
      break
    case "Currency Present":
      addAlert(alerts, "currency", "validation", sev, msg)
      break
    default:
      break
  }
}

function mapAnomalyFlag(alerts: FieldAlerts, flag: AnomalyFlag) {
  const sev: AlertSeverity =
    flag.severity === "high" ? "high" : flag.severity === "medium" ? "medium" : "low"
  const msg = flag.description
  const lineIdx = parseLineIndex(msg)

  switch (flag.flag_type) {
    case "invoice_date_future":
    case "invoice_date_slightly_future":
    case "invoice_date_stale":
    case "invoice_date_old":
      addAlert(alerts, "invoice_date", "anomaly", sev, msg)
      break
    case "due_date_future":
      addAlert(alerts, "due_date", "anomaly", sev, msg)
      break
    case "due_date_before_invoice":
      addAlert(alerts, "due_date", "anomaly", sev, msg)
      addAlert(alerts, "invoice_date", "anomaly", sev, msg)
      break
    case "missing_due_date":
      addAlert(alerts, "due_date", "anomaly", sev, msg)
      break
    case "high_value":
      addAlert(alerts, "total_amount", "anomaly", sev, msg)
      break
    case "invalid_quantity":
    case "negative_line_amount":
      if (lineIdx !== null) addAlert(alerts, `line:${lineIdx}`, "anomaly", sev, msg)
      break
    case "missing_invoice_number":
      addAlert(alerts, "invoice_number", "anomaly", sev, msg)
      break
    case "suspicious_vendor_name":
      addAlert(alerts, "vendor_name", "anomaly", sev, msg)
      break
    default:
      if (/due date/i.test(msg)) addAlert(alerts, "due_date", "anomaly", sev, msg)
      if (/invoice date/i.test(msg)) addAlert(alerts, "invoice_date", "anomaly", sev, msg)
      if (/vendor/i.test(msg)) addAlert(alerts, "vendor_name", "anomaly", sev, msg)
      if (/invoice number/i.test(msg)) addAlert(alerts, "invoice_number", "anomaly", sev, msg)
      if (/total|amount/i.test(msg)) addAlert(alerts, "total_amount", "anomaly", sev, msg)
      if (lineIdx !== null) addAlert(alerts, `line:${lineIdx}`, "anomaly", sev, msg)
      break
  }
}

function parseLocalDate(iso: string | null | undefined): Date | null {
  if (!iso?.trim()) return null
  const d = new Date(`${iso.trim().slice(0, 10)}T12:00:00`)
  return Number.isNaN(d.getTime()) ? null : d
}

function todayLocal(): Date {
  const d = new Date()
  d.setHours(12, 0, 0, 0)
  return d
}

function applyAuthoritativeDateAlerts(alerts: FieldAlerts, inv: ExtractedInvoice) {
  const ref = todayLocal()
  const refLabel = ref.toISOString().slice(0, 10)
  const invDate = parseLocalDate(inv.invoice_date)
  const dueDate = parseLocalDate(inv.due_date)

  const dueAlert = alerts.due_date
  if (dueAlert && dueDate) {
    dueAlert.messages = dueAlert.messages.filter((m) => {
      if (/future/i.test(m) && dueDate.getTime() <= ref.getTime()) {
        return false
      }
      return true
    })
    if (dueAlert.messages.length === 0) {
      delete alerts.due_date
    }
  }

  if (invDate) {
    const daysOld = (ref.getTime() - invDate.getTime()) / 86400000
    if (daysOld > 365) {
      addAlert(
        alerts,
        "invoice_date",
        "anomaly",
        "medium",
        `Invoice date is more than one year before today (${refLabel}).`,
      )
    }
  }

  if (dueDate && dueDate.getTime() > ref.getTime()) {
    addAlert(
      alerts,
      "due_date",
      "anomaly",
      "medium",
      `Due date is after today (${refLabel}).`,
    )
  }
}

export function buildFieldAlerts(report: ProcessingReport): FieldAlerts {
  const alerts: FieldAlerts = {}

  for (const rule of report.validation?.rules ?? []) {
    mapValidationRule(alerts, rule)
  }

  for (const flag of report.anomalies?.flags ?? []) {
    mapAnomalyFlag(alerts, flag)
  }

  if (report.extracted_invoice) {
    applyAuthoritativeDateAlerts(alerts, report.extracted_invoice)
  }

  return alerts
}

export function getTabNotifications(report: ProcessingReport): TabNotifications {
  const alerts = buildFieldAlerts(report)
  const hasDataAlerts = Object.keys(alerts).length > 0
  const failedValidation = (report.validation?.failed_count ?? 0) > 0
  const hasAnomalies = (report.anomalies?.flags.length ?? 0) > 0
  const needsReportAttention =
    !report.decision.includes("Auto-Approve") || report.decision.includes("Reject")

  return {
    extracted: hasDataAlerts,
    validation: failedValidation,
    anomalies: hasAnomalies,
    report: needsReportAttention || (report.next_steps?.length ?? 0) > 0,
  }
}

export function getFieldAlert(alerts: FieldAlerts, key: string): FieldAlert | undefined {
  return alerts[key]
}

export function lineRowHasAlert(alerts: FieldAlerts, index: number): FieldAlert | undefined {
  return alerts[`line:${index}`]
}
