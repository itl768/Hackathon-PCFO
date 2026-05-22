const STORAGE_KEY = "invoice-default-currency"

export interface InvoiceSettings {
  default_currency: string
  supported_currencies: string[]
  approval_threshold: number
}

export function loadStoredCurrency(fallback: string): string {
  if (typeof window === "undefined") return fallback
  return localStorage.getItem(STORAGE_KEY) || fallback
}

export function saveStoredCurrency(code: string) {
  if (typeof window === "undefined") return
  localStorage.setItem(STORAGE_KEY, code)
}
