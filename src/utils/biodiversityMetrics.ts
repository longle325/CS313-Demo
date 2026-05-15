import type {
  BiodiversityRecord,
  DatasetSummary,
  FilterOptions,
  MetricDefinition,
  MetricKey,
} from '../types';
import { formatCompact, formatNumber } from './formatters';

type RawBiodiversityRow = Record<string, string | number | undefined>;

export const METRICS: Record<MetricKey, MetricDefinition> = {
  predictedRichness: {
    key: 'predictedRichness',
    label: 'Vietnam Biodiversity richness index',
    shortLabel: 'Richness index',
    unit: '0–1 index',
    description: 'Model forecast on the same fixed 0–1 richness scale.',
    palette: ['#8d1d2c', '#dfb43f', '#126b50'],
    format: (value) => formatNumber(value, 2),
  },
  normalizedRichness: {
    key: 'normalizedRichness',
    label: 'Vietnam Biodiversity richness index',
    shortLabel: 'Richness index',
    unit: '0–1 index',
    description: 'Observed species richness adjusted by log observation effort, capped at the train p99 and scaled to 0–1.',
    palette: ['#8d1d2c', '#dfb43f', '#126b50'],
    format: (value) => formatNumber(value, 2),
  },
  nSpecies: {
    key: 'nSpecies',
    label: 'Observed species',
    shortLabel: 'Species',
    unit: 'species-cell count',
    description: 'Distinct species reported in a grid cell for the selected year.',
    palette: ['#7f1d1d', '#f2a65a', '#0f766e'],
    format: (value) => formatNumber(value, 0),
  },
  nObservations: {
    key: 'nObservations',
    label: 'GBIF observations',
    shortLabel: 'Observations',
    unit: 'records',
    description: 'Citizen-science occurrence records behind the biodiversity signal.',
    palette: ['#1f3a5f', '#4aa3a2', '#d7f171'],
    format: (value) => formatCompact(value),
  },
  forestCoverPct: {
    key: 'forestCoverPct',
    label: 'Forest cover',
    shortLabel: 'Forest cover',
    unit: '%',
    description: 'Estimated tree cover after cumulative Hansen loss adjustment.',
    palette: ['#5b2c1f', '#b7b653', '#1d6b43'],
    format: (value) => `${formatNumber(value, 1)}%`,
  },
  forestLossHa: {
    key: 'forestLossHa',
    label: 'Forest loss',
    shortLabel: 'Forest loss',
    unit: 'ha',
    description: 'Forest area lost inside the grid cell during the selected year.',
    palette: ['#164e63', '#f0b35a', '#b42318'],
    format: (value) => `${formatNumber(value, 1)} ha`,
  },
  avgTemp: {
    key: 'avgTemp',
    label: 'Average temperature',
    shortLabel: 'Temperature',
    unit: '°C',
    description: 'Annual mean daily temperature from Open-Meteo.',
    palette: ['#22577a', '#f6d365', '#c2410c'],
    format: (value) => `${formatNumber(value, 1)}°C`,
  },
  totalRainfallMm: {
    key: 'totalRainfallMm',
    label: 'Annual rainfall',
    shortLabel: 'Rainfall',
    unit: 'mm',
    description: 'Annual precipitation total from Open-Meteo.',
    palette: ['#6d3f12', '#5fb7b7', '#174ea6'],
    format: (value) => `${formatNumber(value, 0)} mm`,
  },
  nDryDays: {
    key: 'nDryDays',
    label: 'Dry days',
    shortLabel: 'Dry days',
    unit: 'days',
    description: 'Days with precipitation below 1 mm.',
    palette: ['#1e6091', '#fed766', '#9a3412'],
    format: (value) => `${formatNumber(value, 0)} days`,
  },
  nHotDays: {
    key: 'nHotDays',
    label: 'Hot days',
    shortLabel: 'Hot days',
    unit: 'days',
    description: 'Days with maximum temperature above 35°C.',
    palette: ['#155e75', '#facc15', '#dc2626'],
    format: (value) => `${formatNumber(value, 0)} days`,
  },
  tempAnomaly: {
    key: 'tempAnomaly',
    label: 'Temperature anomaly',
    shortLabel: 'Temp anomaly',
    unit: '°C',
    description: 'Difference from the grid cell mean across 2019-2024.',
    palette: ['#2563eb', '#f8fafc', '#dc2626'],
    format: (value) => `${value > 0 ? '+' : ''}${formatNumber(value, 2)}°C`,
  },
};

export const METRIC_KEYS = Object.keys(METRICS) as MetricKey[];

export function parseBiodiversityRows(rows: RawBiodiversityRow[]): BiodiversityRecord[] {
  return rows
    .map((row) => {
      const parsedGrid = parseGridId(String(row.grid_id ?? ''));
      if (!parsedGrid) return null;

      const record: BiodiversityRecord = {
        gridId: String(row.grid_id),
        year: toNumber(row.year),
        lat: parsedGrid.lat,
        lon: parsedGrid.lon,
        forestCoverPct: toNumber(row.forest_cover_pct),
        forestLossHa: toNumber(row.forest_loss_ha),
        forestLossPctChange: toNumber(row.forest_loss_pct_change),
        avgTemp: toNumber(row.avg_temp),
        totalRainfallMm: toNumber(row.total_rainfall_mm),
        nDryDays: toNumber(row.n_dry_days),
        nHotDays: toNumber(row.n_hot_days),
        tempAnomaly: toNumber(row.temp_anomaly),
        nObservations: toNumber(row.n_observations),
        nSpecies: toNumber(row.n_species),
        normalizedRichness: toNumber(row.normalized_richness),
        predictedRichness: Number.NaN,
      };

      return hasUsableRecord(record) ? record : null;
    })
    .filter((record): record is BiodiversityRecord => record !== null);
}

export function filterRecords(
  records: BiodiversityRecord[],
  filters: FilterOptions,
): BiodiversityRecord[] {
  return records.filter(
    (record) =>
      record.year === filters.year && record.nObservations >= filters.minObservations,
  );
}

export function aggregateRecords(records: BiodiversityRecord[]): DatasetSummary {
  const gridCells = new Set(records.map((record) => record.gridId));
  const years = [...new Set(records.map((record) => record.year))].sort((a, b) => a - b);
  const totalObservations = sum(records, 'nObservations');
  const speciesCellCount = sum(records, 'nSpecies');
  const averageRichness = average(records, 'normalizedRichness');
  const averageForestCover = average(records, 'forestCoverPct');
  const totalForestLossHa = sum(records, 'forestLossHa');
  const topGrid = records.reduce<BiodiversityRecord | null>((best, record) => {
    if (!best) return record;
    return record.normalizedRichness > best.normalizedRichness ? record : best;
  }, null);

  return {
    totalRows: records.length,
    gridCells: gridCells.size,
    years,
    totalObservations,
    speciesCellCount,
    averageRichness,
    averageForestCover,
    totalForestLossHa,
    topGrid,
  };
}

export function getMetricValue(record: BiodiversityRecord, metric: MetricKey): number {
  return record[metric];
}

export function getMetricDomain(
  records: BiodiversityRecord[],
  metric: MetricKey,
): { min: number; max: number } {
  if (metric === 'normalizedRichness' || metric === 'predictedRichness') {
    return { min: 0, max: 1 };
  }

  const values = records
    .map((record) => getMetricValue(record, metric))
    .filter(Number.isFinite)
    .sort((a, b) => a - b);

  if (values.length === 0) return { min: 0, max: 1 };
  if (values.length < 20) {
    const min = values[0];
    const max = values[values.length - 1];
    return min === max ? widenDomain(min) : { min, max };
  }

  const min = percentile(values, 0.02);
  const max = percentile(values, 0.98);
  return min === max ? widenDomain(min) : { min, max };
}

export function getAvailableYears(records: BiodiversityRecord[]): number[] {
  return [...new Set(records.map((record) => record.year))].sort((a, b) => a - b);
}

function parseGridId(gridId: string): { lat: number; lon: number } | null {
  // The pipeline encodes the grid centroid directly in grid_id: VN_{lat}_{lon}.
  const match = /^VN_([-0-9.]+)_([-0-9.]+)$/.exec(gridId);
  if (!match) return null;

  const lat = Number(match[1]);
  const lon = Number(match[2]);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  if (lat < 8 || lat > 23.6 || lon < 102 || lon > 110.1) return null;

  return { lat, lon };
}

function toNumber(value: string | number | undefined): number {
  if (value === '') return Number.NaN;

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function hasUsableRecord(record: BiodiversityRecord): boolean {
  return [
    record.year,
    record.lat,
    record.lon,
    record.nObservations,
    record.nSpecies,
    record.normalizedRichness,
  ].every(Number.isFinite);
}

function sum(records: BiodiversityRecord[], key: MetricKey): number {
  return records.reduce((total, record) => total + getMetricValue(record, key), 0);
}

function average(records: BiodiversityRecord[], key: MetricKey): number {
  return records.length === 0 ? 0 : sum(records, key) / records.length;
}

function percentile(sortedValues: number[], q: number): number {
  const index = (sortedValues.length - 1) * q;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  if (lower === upper) return sortedValues[lower];
  return sortedValues[lower] + (sortedValues[upper] - sortedValues[lower]) * (index - lower);
}

function widenDomain(value: number): { min: number; max: number } {
  const spread = Math.abs(value) > 1 ? Math.abs(value) * 0.1 : 1;
  return { min: value - spread, max: value + spread };
}
