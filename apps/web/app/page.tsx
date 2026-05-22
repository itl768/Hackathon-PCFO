"use client"

import { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { InvoiceList } from "@/components/invoicing/invoice-list"
import { Uploader } from "@/components/invoicing/uploader"
import { listInvoices } from "@/lib/api"
import { type InvoiceListItem } from "@/lib/types"

export default function InboxPage() {
  const router = useRouter()
  const [invoices, setInvoices] = useState<InvoiceListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const list = await listInvoices()
      setInvoices(list)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load invoices")
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const handleUploaded = useCallback(
    (invoiceId: string) => {
      router.push(`/invoices/${invoiceId}`)
    },
    [router]
  )

  return (
    <div className="mx-auto flex min-h-svh max-w-4xl flex-col gap-8 px-4 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Invoice Processing Engine</h1>
        <p className="text-sm text-muted-foreground">
          Drop an invoice to run it through the multi-agent review pipeline.
        </p>
      </header>

      <section className="flex flex-col gap-4">
        <Uploader onUploaded={handleUploaded} />
      </section>

      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Recent invoices</h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void refresh()}
            disabled={isLoading}
            aria-label="Refresh invoices"
          >
            <RefreshCw className={isLoading ? "animate-spin" : undefined} />
            Refresh
          </Button>
        </div>
        {error ? (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        ) : (
          <InvoiceList invoices={invoices} />
        )}
      </section>
    </div>
  )
}
