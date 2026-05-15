import { RotateCcw } from 'lucide-react';
import type { MetricKey } from '../types';
import { METRIC_KEYS, METRICS } from '../utils/biodiversityMetrics';

type ControlsPanelProps = {
  years: number[];
  year: number;
  metric: MetricKey;
  minObservations: number;
  onYearChange: (year: number) => void;
  onMetricChange: (metric: MetricKey) => void;
  onMinObservationsChange: (value: number) => void;
  onReset: () => void;
};

export function ControlsPanel({
  years,
  year,
  metric,
  minObservations,
  onYearChange,
  onMetricChange,
  onMinObservationsChange,
  onReset,
}: ControlsPanelProps) {
  const yearIndex = years.indexOf(year);
  const resolvedYearIndex = yearIndex === -1 ? Math.max(0, years.length - 1) : yearIndex;

  return (
    <section className="controls-panel" aria-label="Map controls">
      <div className="range-control">
        <div>
          <label htmlFor="year">Year</label>
          <span>{year}</span>
        </div>
        <input
          id="year"
          min="0"
          max={Math.max(0, years.length - 1)}
          step="1"
          type="range"
          value={resolvedYearIndex}
          disabled={years.length === 0}
          onChange={(event) => {
            const nextIndex = Number(event.target.value);
            const nextYear = years[nextIndex];
            if (nextYear !== undefined) onYearChange(nextYear);
          }}
        />
      </div>

      <div className="control-row">
        <label htmlFor="metric">Color metric</label>
        <select
          id="metric"
          value={metric}
          onChange={(event) => onMetricChange(event.target.value as MetricKey)}
        >
          {METRIC_KEYS.map((metricKey) => (
            <option value={metricKey} key={metricKey}>
              {METRICS[metricKey].label}
            </option>
          ))}
        </select>
      </div>

      <div className="range-control">
        <div>
          <label htmlFor="observations">Minimum observations</label>
          <span>{minObservations.toLocaleString('en-US')}</span>
        </div>
        <input
          id="observations"
          min="0"
          max="100"
          step="5"
          type="range"
          value={minObservations}
          onChange={(event) => onMinObservationsChange(Number(event.target.value))}
        />
      </div>

      <button className="reset-button" type="button" onClick={onReset}>
        <RotateCcw size={16} aria-hidden="true" />
        Reset view
      </button>
    </section>
  );
}
