"use client"

import { Coins } from "lucide-react"

interface CurrencySelectorProps {
  value: string
  options: string[]
  onChange: (code: string) => void
  disabled?: boolean
}

export function CurrencySelector({
  value,
  options,
  onChange,
  disabled,
}: CurrencySelectorProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Coins className="h-3.5 w-3.5" />
        Default currency
      </label>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border bg-background px-3 py-2 text-sm font-medium focus:border-primary focus:outline-none disabled:opacity-50"
      >
        {options.map((code) => (
          <option key={code} value={code}>
            {code}
          </option>
        ))}
      </select>
      <p className="text-[10px] leading-snug text-muted-foreground">
        Used when the invoice does not specify a currency. Server default comes from{" "}
        <code className="rounded bg-muted px-1">INVOICE_DEFAULT_CURRENCY</code> in .env.
      </p>
    </div>
  )
}
