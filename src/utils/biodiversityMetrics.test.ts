import { describe, expect, it } from 'vitest';
import {
  aggregateRecords,
  filterRecords,
  getMetricDomain,
  parseBiodiversityRows,
} from './biodiversityMetrics';

const rawRows = [
  {
    grid_id: 'VN_10.74_106.72',
    year: '2024',
    forest_cover_pct: '1.46',
    forest_loss_ha: '2.43',
    forest_loss_pct_change: '-1.6',
    avg_temp: '28.09',
    total_rainfall_mm: '1900.5',
    n_dry_days: '188',
    n_hot_days: '70',
    temp_anomaly: '0.51',
    n_observations: '4995',
    n_species: '407',
    normalized_richness: '47.7902',
  },
  {
    grid_id: 'VN_11.46_107.44',
    year: '2024',
    forest_cover_pct: '40.94',
    forest_loss_ha: '92.68',
    forest_loss_pct_change: '-2.1',
    avg_temp: '26.56',
    total_rainfall_mm: '2300.1',
    n_dry_days: '129',
    n_hot_days: '28',
    temp_anomaly: '0.32',
    n_observations: '27404',
    n_species: '450',
    normalized_richness: '44.0379',
  },
  {
    grid_id: 'VN_bad_coordinate',
    year: '2024',
    n_observations: '8',
    n_species: '3',
    normalized_richness: '1.3652',
  },
];

describe('biodiversity dataset utilities', () => {
  it('parses grid coordinates and drops unusable rows', () => {
    const records = parseBiodiversityRows(rawRows);

    expect(records).toHaveLength(2);
    expect(records[0]).toMatchObject({
      gridId: 'VN_10.74_106.72',
      lat: 10.74,
      lon: 106.72,
      year: 2024,
      nSpecies: 407,
      normalizedRichness: 47.7902,
    });
  });

  it('filters by year and minimum observation count', () => {
    const records = parseBiodiversityRows(rawRows);

    expect(filterRecords(records, { year: 2024, minObservations: 10000 })).toHaveLength(1);
    expect(filterRecords(records, { year: 2023, minObservations: 0 })).toHaveLength(0);
  });

  it('summarizes records without claiming distinct species identities', () => {
    const summary = aggregateRecords(parseBiodiversityRows(rawRows));

    expect(summary.totalRows).toBe(2);
    expect(summary.gridCells).toBe(2);
    expect(summary.totalObservations).toBe(32399);
    expect(summary.speciesCellCount).toBe(857);
    expect(summary.topGrid?.gridId).toBe('VN_10.74_106.72');
  });

  it('uses one fixed 0-1 map color scale for richness indexes', () => {
    const records = parseBiodiversityRows(rawRows);

    expect(getMetricDomain(records, 'normalizedRichness')).toEqual({
      min: 0,
      max: 1,
    });
  });
});
