export function formatMoney(
  amount: number | null | undefined,
  currency: string | null | undefined
): string {
  if (amount === null || amount === undefined) return "—"
  const code = currency?.trim() || "USD"
  return `${amount.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} ${code}`
}

export function formatListDate(iso: string | null | undefined): string {
  if (!iso) return "—"
  const parsed = new Date(iso + (iso.includes("T") ? "" : "T00:00:00"))
  if (Number.isNaN(parsed.getTime())) return "—"
  return parsed.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

export function formatReceivedAt(iso: string): string {
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return "—"
  return parsed.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}
