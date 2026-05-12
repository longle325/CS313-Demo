import { BarChart3, Crosshair, RotateCcw } from 'lucide-react';
import type { BiodiversityRecord, DatasetSummary, MetricKey } from '../types';
import { METRIC_KEYS, METRICS } from '../utils/biodiversityMetrics';
import { formatCoordinate, formatNumber } from '../utils/formatters';

type InsightsPanelProps = {
  years: number[];
  year: number;
  metric: MetricKey;
  minObservations: number;
  summary: DatasetSummary;
  records: BiodiversityRecord[];
  selectedRecord: BiodiversityRecord | null;
  onYearChange: (year: number) => void;
  onMetricChange: (metric: MetricKey) => void;
  onMinObservationsChange: (value: number) => void;
  onSelectRecord: (record: BiodiversityRecord) => void;
  onReset: () => void;
};

export function InsightsPanel({
  years,
  year,
  metric,
  minObservations,
  summary,
  records,
  selectedRecord,
  onYearChange,
  onMetricChange,
  onMinObservationsChange,
  onSelectRecord,
  onReset,
}: InsightsPanelProps) {
  const metricDefinition = METRICS[metric];
  const rankedRecords = records
    .slice()
    .sort((a, b) => b[metric] - a[metric])
    .slice(0, 80);
  const activeRecord = selectedRecord ?? rankedRecords[0] ?? null;
  const selectedDetails = activeRecord
    ? [
        {
          label: metricDefinition.shortLabel,
          value: metricDefinition.format(activeRecord[metric]),
        },
        metric === 'normalizedRichness'
          ? null
          : {
              label: 'Richness',
              value: METRICS.normalizedRichness.format(activeRecord.normalizedRichness),
            },
        { label: 'Species', value: formatNumber(activeRecord.nSpecies) },
        { label: 'Observations', value: formatNumber(activeRecord.nObservations) },
        { label: 'Forest loss', value: METRICS.forestLossHa.format(activeRecord.forestLossHa) },
      ].filter((item): item is { label: string; value: string } => item !== null)
    : [];

  return (
    <aside className="insights-panel" aria-label="Map filters and selected grid cells">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Vietnam grid map</p>
          <h1>Biodiversity demo</h1>
        </div>
        <button className="icon-button" type="button" onClick={onReset} aria-label="Reset filters">
          <RotateCcw size={17} aria-hidden="true" />
        </button>
      </div>

      <section className="compact-controls" aria-label="Filters">
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
          <label htmlFor="metric">Metric</label>
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
            <label htmlFor="observations">Min observations</label>
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
      </section>

      <section className="panel-stats" aria-label="Filtered dataset summary">
        <article>
          <span>{formatNumber(summary.totalRows)}</span>
          <p>points shown</p>
        </article>
        <article>
          <span>{formatNumber(summary.gridCells)}</span>
          <p>grid cells</p>
        </article>
        <article>
          <span>{formatNumber(summary.averageRichness, 2)}</span>
          <p>mean richness</p>
        </article>
      </section>

      <section className="selected-card" aria-label="Selected grid cell">
        <div className="selected-card-title">
          <Crosshair size={17} aria-hidden="true" />
          <h2>Selected point</h2>
        </div>
        {activeRecord ? (
          <>
            <strong>{activeRecord.gridId}</strong>
            <p>
              {formatCoordinate(activeRecord.lat)}, {formatCoordinate(activeRecord.lon)}
            </p>
            <dl>
              {selectedDetails.map((detail) => (
                <div key={detail.label}>
                  <dt>{detail.label}</dt>
                  <dd>{detail.value}</dd>
                </div>
              ))}
            </dl>
          </>
        ) : (
          <p>No point matches the current filters.</p>
        )}
      </section>

      <section className="point-list-section" aria-label="Ranked visible points">
        <div className="list-heading">
          <div>
            <BarChart3 size={17} aria-hidden="true" />
            <h2>Top visible points</h2>
          </div>
          <span>{metricDefinition.shortLabel}</span>
        </div>
        <div className="point-list">
          {rankedRecords.map((record) => {
            const isSelected = record.gridId === activeRecord?.gridId;
            return (
              <button
                className={isSelected ? 'point-row selected' : 'point-row'}
                key={record.gridId}
                type="button"
                onClick={() => onSelectRecord(record)}
              >
                <span>
                  <strong>{record.gridId}</strong>
                  <small>
                    {formatCoordinate(record.lat)}, {formatCoordinate(record.lon)}
                  </small>
                </span>
                <em>{metricDefinition.format(record[metric])}</em>
              </button>
            );
          })}
        </div>
      </section>
    </aside>
  );
}
