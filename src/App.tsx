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
} from './utils/biodiversityMetrics';

function App() {
  const [records, setRecords] = useState<BiodiversityRecord[]>([]);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState('');
  const [selectedYear, setSelectedYear] = useState(2024);
  const [minObservations, setMinObservations] = useState(0);
  const [selectedGridId, setSelectedGridId] = useState<string | null>(null);

  useEffect(() => {
    loadBiodiversityData()
      .then((loadedRecords) => {
        setRecords(loadedRecords);
        setSelectedYear(2024);
        setStatus('ready');
      })
      .catch((error: unknown) => {
        setErrorMessage(error instanceof Error ? error.message : 'Unknown data loading error');
        setStatus('error');
      });
  }, []);

  const mapMetric: MetricKey = 'normalizedRichness';
  const years = useMemo(() => getAvailableYears(records), [records]);
  const filteredRecords = useMemo(
    () => filterRecords(records, { year: selectedYear, minObservations }),
    [records, selectedYear, minObservations],
  );
  const filteredSummary = useMemo(() => aggregateRecords(filteredRecords), [filteredRecords]);
  const selectedRecord = useMemo(
    () => filteredRecords.find((record) => record.gridId === selectedGridId) ?? null,
    [filteredRecords, selectedGridId],
  );

  function resetControls() {
    setSelectedYear(2024);
    setMinObservations(0);
    setSelectedGridId(null);
  }

  function handleMinObservationsChange(value: number) {
    setMinObservations(value);
    setSelectedGridId(null);
  }

  function handleYearChange(year: number) {
    setSelectedYear(year);
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
                <h2>Vietnam Biodiversity richness index</h2>
              </div>
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

export default App;
