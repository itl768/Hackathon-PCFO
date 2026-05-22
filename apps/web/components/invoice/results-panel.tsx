"use client"

import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Download,
  FileText,
  ShieldCheck,
  Search,
  ClipboardList,
} from "lucide-react"
import { useMemo, useState } from "react"

import {
  buildFieldAlerts,
  getFieldAlert,
  getTabNotifications,
  lineRowHasAlert,
  type FieldAlerts,
} from "@/lib/invoice-field-alerts"
import type { ProcessingReport } from "@/lib/invoice-types"
import { cn } from "@/lib/utils"
import { RiskGauge } from "./risk-gauge"

interface ResultsPanelProps {
  report: ProcessingReport | null
}

type Tab = "extracted" | "validation" | "anomalies" | "report"

const TABS: { id: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "extracted", label: "Data", icon: FileText },
  { id: "validation", label: "Validation", icon: ShieldCheck },
  { id: "anomalies", label: "Anomalies", icon: Search },
  { id: "report", label: "Report", icon: ClipboardList },
]

export function ResultsPanel({ report }: ResultsPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>("extracted")

  const fieldAlerts = useMemo(
    () => (report ? buildFieldAlerts(report) : {}),
    [report],
  )
  const tabNotifications = useMemo(
    () => (report ? getTabNotifications(report) : null),
    [report],
  )

  if (!report) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center">
        <FileText className="mb-3 h-10 w-10 text-muted-foreground/30" />
        <p className="text-sm text-muted-foreground">
          Process an invoice to see results
        </p>
      </div>
    )
  }

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `invoice-report-${report.extracted_invoice?.invoice_number || "unknown"}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const decisionColor =
    report.decision.includes("Approve") && !report.decision.includes("Reject")
      ? "bg-emerald-500/10 text-emerald-700 border-emerald-500/30"
      : report.decision.includes("Reject")
        ? "bg-red-500/10 text-red-700 border-red-500/30"
        : "bg-amber-500/10 text-amber-700 border-amber-500/30"

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Results
      </h3>

      <div className="flex items-center gap-4">
        <RiskGauge score={report.risk_score} size={90} />
        <div className="flex flex-col gap-2">
          <span
            className={`inline-flex rounded-lg border px-3 py-1.5 text-xs font-bold ${decisionColor}`}
          >
            {report.decision}
          </span>
          <span className="text-[10px] text-muted-foreground">
            Confidence: {report.confidence}
          </span>
        </div>
      </div>

      <div className="flex rounded-lg border bg-muted/30 p-0.5">
        {TABS.map((tab) => {
          const hasNotification = tabNotifications?.[tab.id] ?? false
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "relative flex flex-1 items-center justify-center gap-1 rounded-md px-2 py-1.5 text-[10px] font-medium transition-all",
                activeTab === tab.id
                  ? "bg-background shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <tab.icon className="h-3 w-3" />
              {tab.label}
              {hasNotification && (
                <span
                  className="absolute right-1 top-0.5 h-2 w-2 rounded-full bg-red-500 ring-2 ring-background"
                  aria-label={`${tab.label} has notifications`}
                />
              )}
            </button>
          )
        })}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {activeTab === "extracted" && (
          <ExtractedDataTab report={report} fieldAlerts={fieldAlerts} />
        )}
        {activeTab === "validation" && <ValidationTab report={report} />}
        {activeTab === "anomalies" && <AnomaliesTab report={report} />}
        {activeTab === "report" && (
          <ReportTab report={report} needsAttention={tabNotifications?.report ?? false} />
        )}
      </div>

      <button
        type="button"
        onClick={handleExport}
        className="flex items-center justify-center gap-2 rounded-lg border bg-muted/30 px-3 py-2 text-xs font-medium transition-all hover:bg-muted"
      >
        <Download className="h-3.5 w-3.5" />
        Export JSON
      </button>
    </div>
  )
}

function ExtractedDataTab({
  report,
  fieldAlerts,
}: {
  report: ProcessingReport
  fieldAlerts: FieldAlerts
}) {
  const inv = report.extracted_invoice
  if (!inv) return <p className="text-xs text-muted-foreground">No data extracted</p>

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-2">
        <Field label="Vendor" value={inv.vendor_name} fieldKey="vendor_name" alerts={fieldAlerts} />
        <Field label="Invoice #" value={inv.invoice_number} fieldKey="invoice_number" alerts={fieldAlerts} />
        <Field label="Payment ref." value={inv.payment_reference} fieldKey="payment_reference" alerts={fieldAlerts} />
        <Field label="IBAN" value={inv.vendor_iban} fieldKey="vendor_iban" alerts={fieldAlerts} />
        <Field label="VAT no." value={inv.vendor_vat_number} fieldKey="vendor_vat_number" alerts={fieldAlerts} />
        <Field label="Country" value={inv.vendor_country} fieldKey="vendor_country" alerts={fieldAlerts} />
        <Field label="Date" value={inv.invoice_date} fieldKey="invoice_date" alerts={fieldAlerts} />
        <Field label="Due Date" value={inv.due_date} fieldKey="due_date" alerts={fieldAlerts} />
        <Field label="Currency" value={inv.currency} fieldKey="currency" alerts={fieldAlerts} />
        <Field
          label="VAT reversed"
          value={inv.vat_reversed ? "Yes" : "No"}
          fieldKey="vat_reversed"
          alerts={fieldAlerts}
        />
      </div>

      {inv.line_items.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase text-muted-foreground">
            Line Items
          </p>
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="border-b bg-muted/30">
                  <th className="px-2 py-1 text-left font-medium">GL</th>
                  <th className="px-2 py-1 text-left font-medium">Description</th>
                  <th className="px-2 py-1 text-right font-medium">Net</th>
                  <th className="px-2 py-1 text-right font-medium">VAT%</th>
                  <th className="px-2 py-1 text-right font-medium">VAT</th>
                  <th className="px-2 py-1 text-right font-medium">Total</th>
                </tr>
              </thead>
              <tbody>
                {inv.line_items.map((item, i) => {
                  const rowAlert = lineRowHasAlert(fieldAlerts, i)
                  return (
                    <tr
                      key={i}
                      className={cn(
                        "border-b last:border-0",
                        rowAlert && "field-alert-flash bg-red-500/5",
                      )}
                      title={rowAlert?.messages.join(" · ")}
                    >
                      <td className="px-2 py-1 text-muted-foreground">{item.gl_account || "—"}</td>
                      <td className="px-2 py-1">{item.description}</td>
                      <td className="px-2 py-1 text-right">{item.net_amount.toFixed(2)}</td>
                      <td className="px-2 py-1 text-right">{item.vat_rate ?? 0}%</td>
                      <td className="px-2 py-1 text-right">{item.vat_amount.toFixed(2)}</td>
                      <td className="px-2 py-1 text-right font-medium">
                        {item.line_total.toFixed(2)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-2">
        <Field label="Subtotal" value={inv.subtotal?.toFixed(2)} fieldKey="subtotal" alerts={fieldAlerts} />
        <Field label="VAT Total" value={inv.vat_total?.toFixed(2)} fieldKey="vat_total" alerts={fieldAlerts} />
        <Field
          label="Total"
          value={inv.total_amount?.toFixed(2)}
          fieldKey="total_amount"
          alerts={fieldAlerts}
          highlight
        />
      </div>
    </div>
  )
}

function ValidationTab({ report }: { report: ProcessingReport }) {
  const val = report.validation
  if (!val) return <p className="text-xs text-muted-foreground">No validation data</p>

  return (
    <div className="flex flex-col gap-2">
      {val.rules.map((rule, i) => (
        <div
          key={i}
          className={cn(
            "flex items-start gap-2 rounded-lg border p-2.5",
            rule.passed
              ? "border-emerald-500/20 bg-emerald-500/5"
              : "field-alert-flash border-red-500/40 bg-red-500/5",
          )}
        >
          {rule.passed ? (
            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" />
          ) : (
            <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" />
          )}
          <div>
            <p className="text-xs font-medium">{rule.rule_name}</p>
            <p className="text-[10px] text-muted-foreground">{rule.message}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

function AnomaliesTab({ report }: { report: ProcessingReport }) {
  const anomalies = report.anomalies
  if (!anomalies || anomalies.flags.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-6">
        <CheckCircle2 className="h-8 w-8 text-emerald-500/50" />
        <p className="text-xs text-muted-foreground">No anomalies detected</p>
      </div>
    )
  }

  const severityColor = (s: string) =>
    s === "high"
      ? "bg-red-500/10 text-red-700 border-red-500/30"
      : s === "medium"
        ? "bg-amber-500/10 text-amber-700 border-amber-500/30"
        : "bg-blue-500/10 text-blue-700 border-blue-500/30"

  return (
    <div className="flex flex-col gap-2">
      {anomalies.flags.map((flag, i) => (
          <div
            key={i}
            className="field-alert-flash rounded-lg border border-red-500/40 bg-red-500/5 p-2.5"
          >
            <div className="mb-1 flex items-center gap-2">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
              <span className="text-xs font-medium">{flag.flag_type}</span>
              <span
                className={`rounded-md border px-1.5 py-0.5 text-[9px] font-bold uppercase ${severityColor(flag.severity)}`}
              >
                {flag.severity}
              </span>
            </div>
            <p className="text-[10px] text-muted-foreground">{flag.description}</p>
          </div>
      ))}
    </div>
  )
}

function ReportTab({
  report,
  needsAttention,
}: {
  report: ProcessingReport
  needsAttention: boolean
}) {
  return (
    <div className="flex flex-col gap-3">
      <div
        className={cn(
          "rounded-lg border bg-muted/20 p-3",
          needsAttention && "field-alert-flash border-amber-500/50 bg-amber-500/5",
        )}
      >
        <p className="text-xs leading-relaxed">{report.summary}</p>
      </div>

      {report.next_steps.length > 0 && (
        <div
          className={cn(
            needsAttention && "field-alert-flash rounded-lg border border-amber-500/40 bg-amber-500/5 p-2",
          )}
        >
          <p className="mb-1 text-[10px] font-semibold uppercase text-muted-foreground">
            Next Steps
          </p>
          <ul className="flex flex-col gap-1">
            {report.next_steps.map((step, i) => (
              <li key={i} className="flex items-start gap-1.5 text-[11px]">
                <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-primary" />
                {step}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function Field({
  label,
  value,
  fieldKey,
  alerts,
  highlight,
}: {
  label: string
  value: string | null | undefined
  fieldKey: string
  alerts: FieldAlerts
  highlight?: boolean
}) {
  const alert = getFieldAlert(alerts, fieldKey)

  return (
    <div
      className={cn(
        "rounded-lg border bg-muted/20 p-2",
        alert && "field-alert-flash bg-red-500/5",
      )}
      title={alert?.messages.join("\n")}
    >
      <div className="flex items-center justify-between gap-1">
        <p className="text-[9px] font-medium uppercase text-muted-foreground">{label}</p>
        {alert && (
          <span className="flex items-center gap-0.5" title="Field has validation or anomaly alert">
            <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
            <AlertTriangle className="h-3 w-3 text-red-500" />
          </span>
        )}
      </div>
      <p className={cn("text-xs", highlight || alert ? "font-bold" : "font-medium")}>
        {value || "—"}
      </p>
      {alert && (
        <p className="mt-1 text-[9px] leading-snug text-red-600 dark:text-red-400">
          {alert.messages[0]}
        </p>
      )}
    </div>
  )
}
