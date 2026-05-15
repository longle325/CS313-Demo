import { BarChart3, Crosshair, RotateCcw } from 'lucide-react';
import type { BiodiversityRecord, DatasetSummary, MetricKey } from '../types';
import { METRIC_KEYS, METRICS } from '../utils/biodiversityMetrics';
import { formatCompact, formatCoordinate, formatNumber } from '../utils/formatters';

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
  type DetailItem = {
    id: string;
    label: string;
    value: string;
  };
  const yearIndex = years.indexOf(year);
  const resolvedYearIndex = yearIndex === -1 ? Math.max(0, years.length - 1) : yearIndex;
  const rankedRecords = records
    .slice()
    .sort((a, b) => b[metric] - a[metric])
    .slice(0, 80);
  const activeRecord = selectedRecord ?? rankedRecords[0] ?? null;
  const selectedDetails = activeRecord
    ? [
        {
          id: metric,
          label: metricDefinition.shortLabel,
          value: metricDefinition.format(activeRecord[metric]),
        },
        metric === 'normalizedRichness'
          ? null
          : {
              id: 'normalizedRichness',
              label: 'Richness',
              value: METRICS.normalizedRichness.format(activeRecord.normalizedRichness),
            },
        metric === 'nSpecies'
          ? null
          : { id: 'nSpecies', label: 'Species', value: formatNumber(activeRecord.nSpecies) },
        metric === 'nObservations'
          ? null
          : {
              id: 'nObservations',
              label: 'Observations',
              value: formatNumber(activeRecord.nObservations),
            },
        metric === 'forestLossHa'
          ? null
          : {
              id: 'forestLossHa',
              label: 'Forest loss',
              value: METRICS.forestLossHa.format(activeRecord.forestLossHa),
            },
      ].filter((item): item is DetailItem => item !== null)
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
          <span>{formatCompact(summary.totalObservations)}</span>
          <p>observations</p>
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
            <div className="selected-meta">
              <strong>{activeRecord.gridId}</strong>
              <span>
                {formatCoordinate(activeRecord.lat)}, {formatCoordinate(activeRecord.lon)}
              </span>
            </div>
            <dl>
              {selectedDetails.map((detail) => (
                <div key={detail.id}>
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
