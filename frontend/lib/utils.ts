import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("pt-BR").format(value);
}

export function formatPercent(value: number, fractionDigits = 1): string {
  return `${value.toFixed(fractionDigits).replace(".", ",")}%`;
}

/**
 * All dates in this app are date-only (no time-of-day) values like
 * "2024-01-01" from the API. `new Date("2024-01-01")` parses that as
 * UTC midnight; formatting it in a negative-UTC-offset timezone (e.g.
 * America/Sao_Paulo, this app's whole audience) rolls it back to the
 * previous day. Forcing timeZone: "UTC" on the formatter -- not on the
 * parse -- keeps the calendar date exactly what the string says,
 * regardless of the viewer's local timezone.
 */
export function formatDate(value: string | Date): string {
  if (!value) return "—";
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function formatMonth(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat("pt-BR", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}
