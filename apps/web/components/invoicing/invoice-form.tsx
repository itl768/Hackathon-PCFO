"use client"

import { AlertCircle } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  type ExtractionFields,
  type Finding,
  type LineItem,
} from "@/lib/types"

interface InvoiceFormProps {
  extraction: ExtractionFields | null
  anomalies: Finding[]
  validationErrors: Finding[]
}

export function InvoiceForm({ extraction, anomalies, validationErrors }: InvoiceFormProps) {
  const findingsByField = collectFindingsByField([...anomalies, ...validationErrors])
  const extractionComplete = extraction !== null

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Extracted Fields
      </h2>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field
          label="Invoice number"
          value={extraction?.invoice_number}
          findings={findingsByField.get("invoice_number")}
          extractionComplete={extractionComplete}
        />
        <Field
          label="Vendor"
          value={extraction?.vendor_name}
          findings={findingsByField.get("vendor_name")}
          extractionComplete={extractionComplete}
        />
        <Field
          label="Invoice date"
          value={extraction?.invoice_date}
          findings={findingsByField.get("invoice_date")}
          extractionComplete={extractionComplete}
        />
        <Field
          label="Due date"
          value={extraction?.due_date}
          findings={findingsByField.get("due_date")}
          extractionComplete={extractionComplete}
        />
        <Field
          label="Total amount"
          value={formatNumber(extraction?.total_amount, extraction?.currency)}
          findings={findingsByField.get("total_amount")}
          extractionComplete={extractionComplete}
        />
        <Field
          label="Tax amount"
          value={formatNumber(extraction?.tax_amount, extraction?.currency)}
          findings={findingsByField.get("tax_amount")}
          extractionComplete={extractionComplete}
        />
      </div>

      <LineItemsTable
        items={extraction?.line_items ?? []}
        findings={findingsByField.get("line_items")}
        extractionComplete={extractionComplete}
      />
    </div>
  )
}

function Field({
  label,
  value,
  findings,
  extractionComplete,
}: {
  label: string
  value: string | null | undefined
  findings?: Finding[]
  extractionComplete: boolean
}) {
  const hasFindings = findings && findings.length > 0
  const isMissing = value === null || value === undefined || value === ""
  const emptyCopy = extractionComplete ? "Not on the invoice" : "Waiting for extraction"

  return (
    <div
      className={cn(
        "flex flex-col gap-1 rounded-md border border-border bg-card px-3 py-2",
        hasFindings && "border-destructive/60 ring-1 ring-destructive/30"
      )}
    >
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <span
        className={cn(
          "text-sm",
          isMissing && "italic text-muted-foreground"
        )}
      >
        {isMissing ? emptyCopy : value}
      </span>
      {hasFindings && (
        <ul className="mt-1 space-y-1">
          {findings.map((finding, idx) => (
            <li
              key={`${finding.source_agent}-${idx}`}
              className="flex items-start gap-1.5 text-xs text-destructive"
            >
              <AlertCircle className="mt-0.5 size-3 shrink-0" />
              <span>{finding.message}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function LineItemsTable({
  items,
  findings,
  extractionComplete,
}: {
  items: LineItem[]
  findings?: Finding[]
  extractionComplete: boolean
}) {
  const hasFindings = findings && findings.length > 0
  const emptyCopy = extractionComplete
    ? "No line items on the invoice"
    : "Waiting for extraction"
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Line items
        </h3>
        {hasFindings && (
          <span className="text-xs text-destructive">
            {findings!.length} finding{findings!.length === 1 ? "" : "s"}
          </span>
        )}
      </div>
      <div
        className={cn(
          "overflow-hidden rounded-md border border-border",
          hasFindings && "border-destructive/60"
        )}
      >
        <table className="w-full text-sm">
          <thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Name</th>
              <th className="px-3 py-2 text-right font-medium">Qty</th>
              <th className="px-3 py-2 text-right font-medium">Unit price</th>
              <th className="px-3 py-2 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="px-3 py-4 text-center italic text-muted-foreground"
                >
                  {emptyCopy}
                </td>
              </tr>
            ) : (
              items.map((item, idx) => (
                <tr key={idx} className="border-t border-border">
                  <td className="px-3 py-2">{item.name || "-"}</td>
                  <td className="px-3 py-2 text-right">{item.quantity}</td>
                  <td className="px-3 py-2 text-right">{item.unit_price.toFixed(2)}</td>
                  <td className="px-3 py-2 text-right">{item.total.toFixed(2)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function collectFindingsByField(findings: Finding[]): Map<string, Finding[]> {
  const map = new Map<string, Finding[]>()
  for (const finding of findings) {
    const key = finding.field_path.split(/[.[]/)[0] || finding.field_path
    const existing = map.get(key)
    if (existing) {
      existing.push(finding)
    } else {
      map.set(key, [finding])
    }
  }
  return map
}

function formatNumber(value: number | null | undefined, currency: string | undefined): string | null {
  if (value === null || value === undefined) return null
  return `${value.toFixed(2)} ${currency ?? ""}`.trim()
}
