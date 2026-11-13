import type { Status } from "./api";
import { statusLabel } from "./format";

export function StatusBadge({ status }: Readonly<{ status: Status }>) {
  return <span className={`badge ${status}`}>{statusLabel(status)}</span>;
}
