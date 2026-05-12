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
  return (
    <section className="controls-panel" aria-label="Map controls">
      <div className="control-row">
        <label htmlFor="year">Year</label>
        <select id="year" value={year} onChange={(event) => onYearChange(Number(event.target.value))}>
          {years.map((availableYear) => (
            <option value={availableYear} key={availableYear}>
              {availableYear}
            </option>
          ))}
        </select>
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
