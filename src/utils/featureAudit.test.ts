import { describe, expect, it } from 'vitest';
import { hasCompleteFeatureAudit } from './featureAudit';

describe('feature audit utilities', () => {
  it('rejects stale explanation responses without value and median fields', () => {
    expect(
      hasCompleteFeatureAudit([
        {
          feature_key: 'prior_records_for_cell',
          feature_label: 'Prior records for cell',
          contribution: 0.2,
          direction: 'positive',
        },
      ]),
    ).toBe(false);
  });

  it('accepts current all-feature audit responses', () => {
    expect(
      hasCompleteFeatureAudit([
        {
          feature_key: 'forest_cover_pct',
          feature_label: 'Forest cover',
          value: 30,
          reference_value: 22.77,
          contribution: 0.04,
          direction: 'positive',
        },
        {
          feature_key: 'years_since_seen',
          feature_label: 'Years since seen',
          value: 1,
          reference_value: 2,
          contribution: -0.01,
          direction: 'negative',
        },
      ], 2),
    ).toBe(true);
  });
});
