import type { Status } from "./api";

const dollars = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

const day = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeZone: "UTC",
});

const time = new Intl.DateTimeFormat("en-US", { timeStyle: "medium" });

const moment = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function money(amount: number): string {
  return dollars.format(amount);
}

// A calendar date from the records, such as 2026-06-24, shown as written.
export function date(iso: string): string {
  return day.format(new Date(iso));
}

// A moment the system recorded, shown in the viewer's time zone.
export function when(iso: string): string {
  return moment.format(new Date(iso));
}

export function clock(iso: string): string {
  return time.format(new Date(iso));
}

export function words(code: string): string {
  const text = code.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export const STATUSES: Status[] = [
  "waiting",
  "in_progress",
  "awaiting_signoff",
  "decided",
];

export const STATUS_LABELS: Record<Status, string> = {
  waiting: "Waiting",
  in_progress: "In progress",
  awaiting_signoff: "Awaiting sign-off",
  decided: "Decided",
};
