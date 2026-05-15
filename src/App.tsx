import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { loadBiodiversityData } from './data/loadBiodiversityData';
import { InsightsPanel } from './components/InsightsPanel';
import { VietnamMap } from './components/VietnamMap';
import type { BiodiversityRecord, MetricKey } from './types';
import {
  aggregateRecords,
  filterRecords,
  getAvailableYears,
  METRICS,
} from './utils/biodiversityMetrics';

const DEFAULT_METRIC: MetricKey = 'normalizedRichness';

function App() {
  const [records, setRecords] = useState<BiodiversityRecord[]>([]);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState('');
  const [selectedYear, setSelectedYear] = useState(2024);
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>(DEFAULT_METRIC);
  const [minObservations, setMinObservations] = useState(0);
  const [selectedGridId, setSelectedGridId] = useState<string | null>(null);

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

  const years = useMemo(() => getAvailableYears(records), [records]);
  const yearLabel = years.length > 0 ? `${years[0]}-${years[years.length - 1]}` : '2009-2024';
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
    if (years.length > 0) setSelectedYear(years[years.length - 1]);
    setSelectedMetric(DEFAULT_METRIC);
    setMinObservations(0);
    setSelectedGridId(null);
  }

  function handleYearChange(year: number) {
    setSelectedYear(year);
    setSelectedGridId(null);
  }

  function handleMetricChange(metric: MetricKey) {
    setSelectedMetric(metric);
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
                <p className="eyebrow">CS313 · {yearLabel} · {fullSummary.gridCells.toLocaleString('en-US')} grid cells</p>
                <h2>{METRICS[selectedMetric].label} in Vietnam, {selectedYear}</h2>
              </div>
              <p>
                Points are Vietnam grid-year records from GBIF and Hansen forest data.
                <br />
                Available Open-Meteo weather is shown when present.
              </p>
            </div>
            <VietnamMap
              records={filteredRecords}
              metric={selectedMetric}
              selectedGridId={selectedGridId}
              onSelectRecord={(record) => setSelectedGridId(record.gridId)}
            />
          </div>
          <InsightsPanel
            years={years}
            year={selectedYear}
            metric={selectedMetric}
            minObservations={minObservations}
            summary={filteredSummary}
            records={filteredRecords}
            selectedRecord={selectedRecord}
            onYearChange={handleYearChange}
            onMetricChange={handleMetricChange}
            onMinObservationsChange={handleMinObservationsChange}
            onSelectRecord={(record) => setSelectedGridId(record.gridId)}
            onReset={resetControls}
          />
        </section>
      )}
    </main>
  );
}

export default App;
