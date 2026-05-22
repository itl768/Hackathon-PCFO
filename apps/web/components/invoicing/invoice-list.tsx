"use client"

import Link from "next/link"
import { FileText } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { formatListDate, formatMoney, formatReceivedAt } from "@/lib/format"
import {
  STATUS_LABELS,
  type InvoiceListItem,
  type InvoiceStatus,
} from "@/lib/types"

const STATUS_VARIANT: Record<InvoiceStatus, "default" | "secondary" | "destructive" | "outline"> = {
  received: "outline",
  processing: "secondary",
  duplicate: "destructive",
  reviewed: "default",
  confirmed: "default",
  failed: "destructive",
}

interface InvoiceListProps {
  invoices: InvoiceListItem[]
}

export function InvoiceList({ invoices }: InvoiceListProps) {
  if (invoices.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-muted/30 px-6 py-12 text-center text-sm text-muted-foreground">
        No invoices yet. Drop one above to get started.
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      <div className="hidden border-b border-border bg-muted/50 px-4 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground sm:grid sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto_auto] sm:gap-3">
        <span>Vendor</span>
        <span>Invoice #</span>
        <span>Invoice date</span>
        <span className="text-right">Amount</span>
        <span>Status</span>
        <span className="text-right">Received</span>
      </div>
      <ul className="divide-y divide-border">
        {invoices.map((invoice) => (
          <li key={invoice.invoice_id}>
            <Link
              href={`/invoices/${invoice.invoice_id}`}
              className="block px-4 py-3 transition-colors hover:bg-muted/40 sm:grid sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto_auto] sm:items-center sm:gap-3"
            >
              <div className="flex min-w-0 items-start gap-3 sm:contents">
                <FileText className="mt-0.5 size-5 shrink-0 text-muted-foreground sm:hidden" />
                <div className="min-w-0 flex-1 sm:col-span-1">
                  <div className="truncate text-sm font-semibold">
                    {invoice.vendor_name?.trim() || "—"}
                  </div>
                  <div className="truncate text-xs text-muted-foreground">
                    {invoice.original_filename}
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground sm:hidden">
                    <span>
                      <span className="font-medium text-foreground/80"># </span>
                      {invoice.invoice_number?.trim() || "—"}
                    </span>
                    <span>
                      <span className="font-medium text-foreground/80">Date </span>
                      {formatListDate(invoice.invoice_date)}
                    </span>
                    <span className="tabular-nums font-medium text-foreground">
                      {formatMoney(invoice.total_amount, invoice.currency)}
                    </span>
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1 sm:hidden">
                  <Badge variant={STATUS_VARIANT[invoice.status]} className="capitalize">
                    {STATUS_LABELS[invoice.status]}
                  </Badge>
                  {invoice.duplicate_of && (
                    <span className="text-[10px] text-muted-foreground">Duplicate</span>
                  )}
                </div>
              </div>

              <div className="hidden truncate text-sm sm:block">
                {invoice.invoice_number?.trim() || "—"}
              </div>
              <div className="hidden text-sm sm:block">
                {formatListDate(invoice.invoice_date)}
              </div>
              <div className="hidden text-right text-sm tabular-nums sm:block">
                {formatMoney(invoice.total_amount, invoice.currency)}
              </div>
              <div className="hidden flex-col items-start gap-0.5 sm:flex">
                <Badge variant={STATUS_VARIANT[invoice.status]} className="capitalize">
                  {STATUS_LABELS[invoice.status]}
                </Badge>
                {invoice.duplicate_of && (
                  <span className="text-[10px] text-muted-foreground">Duplicate</span>
                )}
              </div>
              <div className="hidden text-right text-xs text-muted-foreground sm:block">
                {formatReceivedAt(invoice.created_at)}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
