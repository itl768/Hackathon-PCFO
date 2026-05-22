import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function shortenFileName(name: string, maxLength = 26): string {
  if (name.length <= maxLength) return name

  const lastDot = name.lastIndexOf(".")
  const ext = lastDot > 0 ? name.slice(lastDot) : ""
  const base = lastDot > 0 ? name.slice(0, lastDot) : name
  const budget = maxLength - ext.length - 1

  if (budget <= 6) {
    return `${name.slice(0, maxLength - 1)}…`
  }

  const head = Math.ceil(budget * 0.55)
  const tail = budget - head
  return `${base.slice(0, head)}…${base.slice(-tail)}${ext}`
}
