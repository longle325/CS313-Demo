import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { loadBiodiversityData } from './data/loadBiodiversityData';
import { loadPredictions } from './data/loadPredictions';
import { InsightsPanel } from './components/InsightsPanel';
import { VietnamMap } from './components/VietnamMap';
import type { ApiPredictionsResponse } from './data/apiClient';
import type { BiodiversityRecord, MetricKey } from './types';
import {
  aggregateRecords,
  filterRecords,
  getAvailableYears,
} from './utils/biodiversityMetrics';

const FORECAST_YEARS = [2024, 2025];

function App() {
  const [records, setRecords] = useState<BiodiversityRecord[]>([]);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState('');
  const [selectedYear, setSelectedYear] = useState(2024);
  const [minObservations, setMinObservations] = useState(0);
  const [selectedGridId, setSelectedGridId] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');

  useEffect(() => {
    loadBiodiversityData()
      .then((loadedRecords) => {
        setRecords(loadedRecords);
        const years = getAvailableYears(loadedRecords);
        if (years.length > 0) setSelectedYear(years[years.length - 1]);
        setStatus('ready');
      })
      .catch((error: unknown) => {
        setErrorMessage(error instanceof Error ? error.message : 'Unknown data loading error');
        setStatus('error');
      });
  }, []);

  useEffect(() => {
    if (status !== 'ready') return;

    setApiStatus('loading');
    Promise.all(FORECAST_YEARS.map((year) => loadPredictions(year)))
      .then((payloads) => {
        setRecords((previousRecords) => applyForecastPayloads(previousRecords, payloads));
        setApiStatus('ready');
      })
      .catch(() => {
        setApiStatus('error');
      });
  }, [status]);

  const years = useMemo(() => getAvailableYears(records), [records]);
  const mapMetric: MetricKey =
    selectedYear >= 2024 && apiStatus === 'ready' ? 'predictedRichness' : 'normalizedRichness';
  const filteredRecords = useMemo(
    () => filterRecords(records, { year: selectedYear, minObservations }),
    [records, selectedYear, minObservations],
  );
  const fullSummary = useMemo(() => aggregateRecords(records), [records]);
  const filteredSummary = useMemo(() => aggregateRecords(filteredRecords), [filteredRecords]);
  const selectedRecord = useMemo(
    () => filteredRecords.find((record) => record.gridId === selectedGridId) ?? null,
    [filteredRecords, selectedGridId],
  );

  function resetControls() {
    if (years.includes(2024)) {
      setSelectedYear(2024);
    } else if (years.length > 0) {
      setSelectedYear(years[years.length - 1]);
    }
    setMinObservations(0);
    setSelectedGridId(null);
  }

  function handleYearChange(year: number) {
    setSelectedYear(year);
    setSelectedGridId(null);
  }

  function handleMinObservationsChange(value: number) {
    setMinObservations(value);
    setSelectedGridId(null);
  }

  return (
    <main className="app-shell">
      {status === 'loading' && (
        <section className="state-panel">
          <Loader2 className="spin" size={24} aria-hidden="true" />
          <p>Loading biodiversity grid data…</p>
        </section>
      )}

      {status === 'error' && (
        <section className="state-panel error">
          <AlertTriangle size={24} aria-hidden="true" />
          <p>{errorMessage}</p>
        </section>
      )}

      {status === 'ready' && (
        <section className="map-workbench">
          <div className="map-stage">
            <div className="map-titlebar">
              <div>
                <p className="eyebrow">CS313 · Vietnam · {fullSummary.gridCells.toLocaleString('en-US')} grid cells</p>
                <h2>Biodiversity richness index</h2>
              </div>
              <p>
                One fixed 0–1 scale across all years. 2009–2023 are observed history; 2024 is the holdout forecast;
                2025 is a projection year under persistence assumptions.
                {apiStatus === 'error' ? ' Model API is unavailable, so the projection year is hidden.' : ''}
              </p>
            </div>
            <VietnamMap
              records={filteredRecords}
              metric={mapMetric}
              selectedGridId={selectedGridId}
              onSelectRecord={(record) => setSelectedGridId(record.gridId)}
            />
          </div>
          <InsightsPanel
            years={years}
            year={selectedYear}
            metric={mapMetric}
            minObservations={minObservations}
            summary={filteredSummary}
            selectedRecord={selectedRecord}
            onYearChange={handleYearChange}
            onMinObservationsChange={handleMinObservationsChange}
            onReset={resetControls}
          />
        </section>
      )}
    </main>
  );
}

function applyForecastPayloads(
  currentRecords: BiodiversityRecord[],
  payloads: ApiPredictionsResponse[],
): BiodiversityRecord[] {
  const observedRecords = currentRecords.filter((record) => record.year <= 2024);
  const recordsByGrid2024 = new Map(
    observedRecords
      .filter((record) => record.year === 2024)
      .map((record) => [record.gridId, record]),
  );
  const payloadByYear = new Map(payloads.map((payload) => [payload.year, payload]));
  const predictionByYearAndGrid = new Map(
    payloads.map((payload) => [
      payload.year,
      new Map(payload.predictions.map((prediction) => [prediction.grid_id, prediction.prediction])),
    ]),
  );

  const updatedObservedRecords = observedRecords.map((record) => {
    if (record.year !== 2024) return record;
    const prediction = predictionByYearAndGrid.get(2024)?.get(record.gridId);
    return {
      ...record,
      predictedRichness: prediction ?? Number.NaN,
    };
  });

  const projectionRecords = [2025].flatMap((year) => {
    const payload = payloadByYear.get(year);
    if (!payload) return [];
    return payload.predictions.flatMap((prediction) => {
      const template = recordsByGrid2024.get(prediction.grid_id);
      if (!template) return [];
      return {
        ...template,
        year,
        normalizedRichness: prediction.prediction,
        predictedRichness: prediction.prediction,
        forestLossHa: 0,
        forestLossPctChange: 0,
      };
    });
  });

  return [...updatedObservedRecords, ...projectionRecords];
}

export default App;
