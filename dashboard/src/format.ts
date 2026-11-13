import type { Status } from "./api";

const dollars = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

const day = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const monthDay = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

const moment = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  second: "2-digit",
});

export function money(amount: number): string {
  return dollars.format(amount);
}

export function date(isoDate: string): string {
  return day.format(new Date(`${isoDate}T00:00:00Z`));
}

export function dateRange(isoStart: string, isoEnd: string): string {
  const sameYear = isoStart.slice(0, 4) === isoEnd.slice(0, 4);
  const start = sameYear
    ? monthDay.format(new Date(`${isoStart}T00:00:00Z`))
    : date(isoStart);
  return `${start} to ${date(isoEnd)}`;
}

export function time(isoTime: string): string {
  return moment.format(new Date(isoTime));
}

export function label(code: string): string {
  const words = code.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const ADD_ONS: Record<string, string> = {
  adventure_sports: "Adventure Sports",
  pre_existing_waiver: "Pre-Existing Condition Waiver",
  electronics_plus: "Electronics Plus",
};

export function addOn(code: string): string {
  return ADD_ONS[code] ?? label(code);
}

const STATUS_LABELS: Record<Status, string> = {
  waiting: "Waiting",
  in_progress: "In progress",
  awaiting_signoff: "Awaiting sign-off",
  decided: "Decided",
};

export function statusLabel(status: Status): string {
  return STATUS_LABELS[status];
}
