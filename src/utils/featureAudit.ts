import type { ApiExplanationRow } from '../data/apiClient';

type FeatureAuditLike = Partial<ApiExplanationRow>;

export function hasCompleteFeatureAudit(rows: readonly FeatureAuditLike[], minimumRows = 10): boolean {
  return (
    rows.length >= minimumRows &&
    rows.every(
      (row) =>
        Number.isFinite(row.value) &&
        Number.isFinite(row.reference_value) &&
        Number.isFinite(row.contribution),
    )
  );
}
