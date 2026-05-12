import Papa from 'papaparse';
import type { BiodiversityRecord } from '../types';
import { parseBiodiversityRows } from '../utils/biodiversityMetrics';

const DATASET_URL = '/data/dataset.csv';

export async function loadBiodiversityData(): Promise<BiodiversityRecord[]> {
  const response = await fetch(DATASET_URL);
  if (!response.ok) {
    throw new Error(`Could not load ${DATASET_URL}: ${response.status}`);
  }

  const csvText = await response.text();
  const parsed = Papa.parse<Record<string, string>>(csvText, {
    header: true,
    skipEmptyLines: true,
  });

  if (parsed.errors.length > 0) {
    const firstError = parsed.errors[0];
    throw new Error(`CSV parse error on row ${firstError.row}: ${firstError.message}`);
  }

  return parseBiodiversityRows(parsed.data);
}
