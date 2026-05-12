export type MetricKey =
  | 'normalizedRichness'
  | 'nSpecies'
  | 'nObservations'
  | 'forestCoverPct'
  | 'forestLossHa'
  | 'avgTemp'
  | 'totalRainfallMm'
  | 'nDryDays'
  | 'nHotDays'
  | 'tempAnomaly';

export type BiodiversityRecord = {
  gridId: string;
  year: number;
  lat: number;
  lon: number;
  forestCoverPct: number;
  forestLossHa: number;
  forestLossPctChange: number;
  avgTemp: number;
  totalRainfallMm: number;
  nDryDays: number;
  nHotDays: number;
  tempAnomaly: number;
  nObservations: number;
  nSpecies: number;
  normalizedRichness: number;
};

export type MetricDefinition = {
  key: MetricKey;
  label: string;
  shortLabel: string;
  unit: string;
  description: string;
  palette: [string, string, string];
  format: (value: number) => string;
};

export type FilterOptions = {
  year: number;
  minObservations: number;
};

export type DatasetSummary = {
  totalRows: number;
  gridCells: number;
  years: number[];
  totalObservations: number;
  speciesCellCount: number;
  averageRichness: number;
  averageForestCover: number;
  totalForestLossHa: number;
  topGrid: BiodiversityRecord | null;
};
