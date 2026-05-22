"use client"

import Link from "next/link"
import { Copy } from "lucide-react"

import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface DuplicateNoticeProps {
  matchedInvoiceId: string | null
}

export function DuplicateNotice({ matchedInvoiceId }: DuplicateNoticeProps) {
  return (
    <div className="flex flex-col gap-3 rounded-md border border-amber-500/40 bg-amber-500/5 p-4">
      <div className="flex items-center gap-2 text-amber-700 dark:text-amber-300">
        <Copy className="size-5" />
        <span className="font-semibold">Duplicate invoice detected</span>
      </div>
      <p className="text-sm text-muted-foreground">
        We already have this invoice on file. It was identified by matching vendor name, invoice
        number, and invoice date.
      </p>
      {matchedInvoiceId && (
        <Link
          href={`/invoices/${matchedInvoiceId}`}
          className={cn(buttonVariants({ variant: "outline", size: "sm" }), "w-fit")}
        >
          Open the existing invoice
        </Link>
      )}
    </div>
  )
}
