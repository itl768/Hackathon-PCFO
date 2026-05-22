"use client"

import { Loader2, Plus, Save, X } from "lucide-react"
import { useCallback, useEffect, useMemo, useState } from "react"

import { DocumentPreview } from "@/components/invoice/document-preview"
import { Button } from "@/components/ui/button"
import {
  emptyLineItem,
  fetchHistoryInvoice,
  updateHistoryInvoice,
} from "@/lib/invoice-api"
import type { InvoiceHistoryDetail, InvoiceSource, LineItem } from "@/lib/invoice-types"

interface InvoiceEditDrawerProps {
  invoiceId: number | null
  onClose: () => void
  onSaved: () => void
}

function Field({
  label,
  required,
  children,
}: {
  label: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <label className="block space-y-1">
      <span className="text-xs font-medium text-muted-foreground">
        {label}
        {required && <span className="text-destructive"> *</span>}
      </span>
      {children}
    </label>
  )
}

const inputClass =
  "w-full rounded-md border bg-background px-2.5 py-1.5 text-sm focus:border-primary focus:outline-none"

function historyPreviewSource(form: InvoiceHistoryDetail): InvoiceSource | null {
  if (!form.source_text?.trim()) return null
  return {
    kind: "text",
    text: form.source_text,
    label: form.file_name ?? form.invoice_number ?? `Invoice #${form.id}`,
  }
}

export function InvoiceEditDrawer({ invoiceId, onClose, onSaved }: InvoiceEditDrawerProps) {
  const [form, setForm] = useState<InvoiceHistoryDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const previewSource = useMemo(
    () => (form ? historyPreviewSource(form) : null),
    [form],
  )

  useEffect(() => {
    if (invoiceId == null) {
      setForm(null)
      return
    }
    setLoading(true)
    setError(null)
    fetchHistoryInvoice(invoiceId)
      .then(setForm)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false))
  }, [invoiceId])

  const updateField = useCallback(
    <K extends keyof InvoiceHistoryDetail>(key: K, value: InvoiceHistoryDetail[K]) => {
      setForm((prev) => (prev ? { ...prev, [key]: value } : prev))
    },
    [],
  )

  const updateLine = useCallback((index: number, patch: Partial<LineItem>) => {
    setForm((prev) => {
      if (!prev) return prev
      const items = [...prev.line_items]
      items[index] = { ...items[index], ...patch }
      return { ...prev, line_items: items }
    })
  }, [])

  const addLine = useCallback(() => {
    setForm((prev) =>
      prev ? { ...prev, line_items: [...prev.line_items, emptyLineItem()] } : prev,
    )
  }, [])

  const removeLine = useCallback((index: number) => {
    setForm((prev) => {
      if (!prev) return prev
      return { ...prev, line_items: prev.line_items.filter((_, i) => i !== index) }
    })
  }, [])

  const handleSave = async () => {
    if (!form) return
    setSaving(true)
    setError(null)
    try {
      await updateHistoryInvoice(form.id, {
        invoice_number: form.invoice_number,
        payment_reference: form.payment_reference,
        vendor_name: form.vendor_name,
        vendor_iban: form.vendor_iban,
        vendor_vat_number: form.vendor_vat_number,
        vendor_country: form.vendor_country,
        vat_reversed: form.vat_reversed,
        invoice_date: form.invoice_date,
        due_date: form.due_date,
        subtotal: form.subtotal,
        vat_total: form.vat_total,
        total_amount: form.total_amount,
        currency: form.currency,
        payment_terms: form.payment_terms,
        line_items: form.line_items,
      })
      onSaved()
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed")
    } finally {
      setSaving(false)
    }
  }

  if (invoiceId == null) return null

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-[1px]"
        onClick={onClose}
        aria-hidden
      />
      <aside
        className="fixed inset-y-0 right-0 z-50 flex w-[min(92vw,80rem)] max-w-none flex-col border-l bg-background shadow-2xl"
        role="dialog"
        aria-labelledby="invoice-drawer-title"
      >
        <header className="flex shrink-0 items-center justify-between border-b px-5 py-3">
          <div>
            <h2 id="invoice-drawer-title" className="text-sm font-bold">
              Edit invoice
            </h2>
            {form && (
              <p className="text-[10px] text-muted-foreground">
                {form.status} · risk {form.risk_score ?? "—"}
                {form.file_name ? ` · ${form.file_name}` : ""}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="flex min-h-0 flex-1">
          <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-5">
            {loading && (
              <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading…
              </div>
            )}
            {error && !loading && (
              <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </p>
            )}
            {form && !loading && (
              <div className="space-y-6">
                <section className="space-y-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Vendor
                  </h3>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Field label="Company name" required>
                      <input
                        className={inputClass}
                        value={form.vendor_name ?? ""}
                        onChange={(e) => updateField("vendor_name", e.target.value || null)}
                      />
                    </Field>
                    <Field label="Country">
                      <input
                        className={inputClass}
                        value={form.vendor_country ?? ""}
                        onChange={(e) => updateField("vendor_country", e.target.value || null)}
                      />
                    </Field>
                    <Field label="IBAN">
                      <input
                        className={inputClass}
                        value={form.vendor_iban ?? ""}
                        onChange={(e) => updateField("vendor_iban", e.target.value || null)}
                      />
                    </Field>
                    <Field label="VAT number">
                      <input
                        className={inputClass}
                        value={form.vendor_vat_number ?? ""}
                        onChange={(e) => updateField("vendor_vat_number", e.target.value || null)}
                      />
                    </Field>
                  </div>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={form.vat_reversed}
                      onChange={(e) => updateField("vat_reversed", e.target.checked)}
                      className="rounded border"
                    />
                    VAT reversed charge
                  </label>
                </section>

                <section className="space-y-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Document
                  </h3>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Field label="Invoice number" required>
                      <input
                        className={inputClass}
                        value={form.invoice_number ?? ""}
                        onChange={(e) => updateField("invoice_number", e.target.value || null)}
                      />
                    </Field>
                    <Field label="Payment reference">
                      <input
                        className={inputClass}
                        value={form.payment_reference ?? ""}
                        onChange={(e) => updateField("payment_reference", e.target.value || null)}
                      />
                    </Field>
                    <Field label="Invoice date" required>
                      <input
                        type="date"
                        className={inputClass}
                        value={form.invoice_date ?? ""}
                        onChange={(e) => updateField("invoice_date", e.target.value || null)}
                      />
                    </Field>
                    <Field label="Due date">
                      <input
                        type="date"
                        className={inputClass}
                        value={form.due_date ?? ""}
                        onChange={(e) => updateField("due_date", e.target.value || null)}
                      />
                    </Field>
                    <Field label="Currency">
                      <input
                        className={inputClass}
                        value={form.currency}
                        onChange={(e) => updateField("currency", e.target.value)}
                      />
                    </Field>
                    <Field label="Payment terms">
                      <input
                        className={inputClass}
                        value={form.payment_terms ?? ""}
                        onChange={(e) => updateField("payment_terms", e.target.value || null)}
                      />
                    </Field>
                    <Field label="Subtotal">
                      <input
                        type="number"
                        step="0.01"
                        className={inputClass}
                        value={form.subtotal ?? ""}
                        onChange={(e) =>
                          updateField("subtotal", e.target.value ? Number(e.target.value) : null)
                        }
                      />
                    </Field>
                    <Field label="Total VAT">
                      <input
                        type="number"
                        step="0.01"
                        className={inputClass}
                        value={form.vat_total ?? ""}
                        onChange={(e) =>
                          updateField("vat_total", e.target.value ? Number(e.target.value) : null)
                        }
                      />
                    </Field>
                    <Field label="Total amount" required>
                      <input
                        type="number"
                        step="0.01"
                        className={inputClass}
                        value={form.total_amount ?? ""}
                        onChange={(e) =>
                          updateField("total_amount", e.target.value ? Number(e.target.value) : null)
                        }
                      />
                    </Field>
                  </div>
                </section>

                <section className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Line items
                    </h3>
                    <Button type="button" variant="outline" size="xs" onClick={addLine}>
                      <Plus className="h-3 w-3" />
                      Add line
                    </Button>
                  </div>
                  <div className="overflow-x-auto rounded-lg border">
                    <table className="w-full min-w-[640px] text-xs">
                      <thead>
                        <tr className="border-b bg-muted/40">
                          <th className="px-2 py-2 text-left font-medium">GL account</th>
                          <th className="px-2 py-2 text-left font-medium">Description</th>
                          <th className="px-2 py-2 text-right font-medium">Net</th>
                          <th className="px-2 py-2 text-right font-medium">VAT %</th>
                          <th className="px-2 py-2 text-right font-medium">VAT</th>
                          <th className="px-2 py-2 text-right font-medium">Total</th>
                          <th className="w-8" />
                        </tr>
                      </thead>
                      <tbody>
                        {form.line_items.length === 0 ? (
                          <tr>
                            <td colSpan={7} className="px-2 py-4 text-center text-muted-foreground">
                              No line items — add one or re-process the document
                            </td>
                          </tr>
                        ) : (
                          form.line_items.map((line, i) => (
                            <tr key={i} className="border-b last:border-0">
                              <td className="p-1">
                                <input
                                  className={inputClass}
                                  value={line.gl_account ?? ""}
                                  onChange={(e) =>
                                    updateLine(i, { gl_account: e.target.value || null })
                                  }
                                />
                              </td>
                              <td className="p-1">
                                <input
                                  className={inputClass}
                                  value={line.description}
                                  onChange={(e) => updateLine(i, { description: e.target.value })}
                                />
                              </td>
                              <td className="p-1">
                                <input
                                  type="number"
                                  step="0.01"
                                  className={`${inputClass} text-right`}
                                  value={line.net_amount}
                                  onChange={(e) =>
                                    updateLine(i, { net_amount: Number(e.target.value) || 0 })
                                  }
                                />
                              </td>
                              <td className="p-1">
                                <input
                                  type="number"
                                  step="0.01"
                                  className={`${inputClass} text-right`}
                                  value={line.vat_rate ?? ""}
                                  onChange={(e) =>
                                    updateLine(i, {
                                      vat_rate: e.target.value ? Number(e.target.value) : null,
                                    })
                                  }
                                />
                              </td>
                              <td className="p-1">
                                <input
                                  type="number"
                                  step="0.01"
                                  className={`${inputClass} text-right`}
                                  value={line.vat_amount}
                                  onChange={(e) =>
                                    updateLine(i, { vat_amount: Number(e.target.value) || 0 })
                                  }
                                />
                              </td>
                              <td className="p-1">
                                <input
                                  type="number"
                                  step="0.01"
                                  className={`${inputClass} text-right`}
                                  value={line.line_total}
                                  onChange={(e) =>
                                    updateLine(i, { line_total: Number(e.target.value) || 0 })
                                  }
                                />
                              </td>
                              <td className="p-1 text-center">
                                <button
                                  type="button"
                                  onClick={() => removeLine(i)}
                                  className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                                >
                                  <X className="h-3 w-3" />
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </section>
              </div>
            )}
          </div>

          <div className="flex w-[min(420px,38%)] min-w-[18rem] shrink-0 flex-col border-l bg-muted/10">
            <DocumentPreview source={previewSource} />
          </div>
        </div>

        <footer className="flex shrink-0 items-center justify-end gap-2 border-t px-5 py-3">
          <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="button" onClick={handleSave} disabled={!form || saving || loading}>
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save changes
          </Button>
        </footer>
      </aside>
    </>
  )
}
