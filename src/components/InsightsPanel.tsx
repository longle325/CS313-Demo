import { useEffect, useState } from 'react';
import { Crosshair, RotateCcw } from 'lucide-react';
import { api, type ApiGridResponse, type ApiModelOption, type ApiScenarioResponse } from '../data/apiClient';
import type { BiodiversityRecord, DatasetSummary, MetricKey } from '../types';
import { METRICS } from '../utils/biodiversityMetrics';
import { hasCompleteFeatureAudit } from '../utils/featureAudit';
import { formatCoordinate, formatNumber } from '../utils/formatters';

const PROJECTION_YEAR = 2025;
const PROJECTION_BASELINE_LOSS_HA = 0;

type InsightsPanelProps = {
  years: number[];
  year: number;
  metric: MetricKey;
  minObservations: number;
  summary: DatasetSummary;
  selectedRecord: BiodiversityRecord | null;
  onYearChange: (year: number) => void;
  onMinObservationsChange: (value: number) => void;
  onReset: () => void;
};

export function InsightsPanel({
  years,
  year,
  metric,
  minObservations,
  summary,
  selectedRecord,
  onYearChange,
  onMinObservationsChange,
  onReset,
}: InsightsPanelProps) {
  const [gridDetails, setGridDetails] = useState<ApiGridResponse | null>(null);
  const [gridDetailsStatus, setGridDetailsStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [modelOptions, setModelOptions] = useState<ApiModelOption[]>([]);
  const [modelOptionsStatus, setModelOptionsStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [selectedModelId, setSelectedModelId] = useState('');
  const [scenarioCover, setScenarioCover] = useState<number | null>(null);
  const [scenarioLoss, setScenarioLoss] = useState<number | null>(null);
  const [scenarioResult, setScenarioResult] = useState<ApiScenarioResponse | null>(null);
  const [scenarioStatus, setScenarioStatus] = useState<'idle' | 'running' | 'ready' | 'error'>('idle');
  const metricDefinition = METRICS[metric];
  const activeRecord = selectedRecord;
  const baselineCover = toNullableNumber(activeRecord?.forestCoverPct);
  const baselineLoss = activeRecord ? PROJECTION_BASELINE_LOSS_HA : null;
  const canRunInference =
    year === 2024 &&
    activeRecord !== null &&
    selectedModelId !== '' &&
    modelOptionsStatus === 'ready' &&
    scenarioCover !== null &&
    scenarioLoss !== null;
  const featureAuditRows = scenarioResult?.scenario_explanation ?? gridDetails?.explanation ?? [];
  const isFeatureAuditComplete = hasCompleteFeatureAudit(featureAuditRows);

  useEffect(() => {
    let isCurrent = true;
    setModelOptionsStatus('loading');
    api.models()
      .then((data) => {
        if (!isCurrent) return;
        const defaultModelId =
          data.default_model_id ||
          data.models.find((modelOption) => modelOption.is_default)?.model_id ||
          data.models[0]?.model_id ||
          '';
        setModelOptions(data.models);
        setSelectedModelId(defaultModelId);
        setModelOptionsStatus('ready');
      })
      .catch(() => {
        if (!isCurrent) return;
        setModelOptions([]);
        setSelectedModelId('');
        setModelOptionsStatus('error');
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  useEffect(() => {
    setGridDetails(null);
    setGridDetailsStatus('idle');
    setScenarioCover(toNullableNumber(activeRecord?.forestCoverPct));
    setScenarioLoss(activeRecord ? PROJECTION_BASELINE_LOSS_HA : null);
    setScenarioResult(null);
    setScenarioStatus('idle');
  }, [activeRecord?.gridId, year]);

  useEffect(() => {
    setGridDetails(null);
    setGridDetailsStatus('idle');
    setScenarioResult(null);
    setScenarioStatus('idle');
  }, [selectedModelId]);

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
        detailIfFinite('Species', activeRecord.nSpecies, (value) => formatNumber(value)),
        detailIfFinite('Observations', activeRecord.nObservations, (value) => formatNumber(value)),
        detailIfFinite('Forest cover', activeRecord.forestCoverPct, METRICS.forestCoverPct.format),
        detailIfFinite('Forest loss', activeRecord.forestLossHa, METRICS.forestLossHa.format),
      ].filter((item): item is { label: string; value: string } => item !== null)
    : [];

  function runInference() {
    if (!activeRecord || !selectedModelId || scenarioCover === null || scenarioLoss === null) return;

    setGridDetails(null);
    setGridDetailsStatus('loading');
    setScenarioResult(null);
    setScenarioStatus('running');
    Promise.all([
      api.grid(activeRecord.gridId, PROJECTION_YEAR, selectedModelId),
      api.scenario({
        grid_id: activeRecord.gridId,
        year: PROJECTION_YEAR,
        model_id: selectedModelId,
        forest_cover_pct: scenarioCover,
        forest_loss_ha: scenarioLoss,
      }),
    ])
      .then(([gridData, scenarioData]) => {
        setGridDetails(gridData);
        setScenarioResult(scenarioData);
        setGridDetailsStatus('ready');
        setScenarioStatus('ready');
      })
      .catch(() => {
        setGridDetails(null);
        setScenarioResult(null);
        setGridDetailsStatus('error');
        setScenarioStatus('error');
      });
  }

  function resetScenario() {
    setScenarioCover(baselineCover);
    setScenarioLoss(baselineLoss);
    setScenarioResult(null);
    setScenarioStatus('idle');
  }

  return (
    <aside className="insights-panel" aria-label="Map filters and selected grid cells">
      <div className="panel-header">
        <button className="icon-button" type="button" onClick={onReset} aria-label="Reset filters">
          <RotateCcw size={17} aria-hidden="true" />
        </button>
      </div>

      <section className="compact-controls" aria-label="Filters">
        <div className="control-row">
          <label htmlFor="year">Year</label>
          <select
            id="year"
            value={year}
            onChange={(event) => onYearChange(Number(event.target.value))}
          >
            {years.map((availableYear) => (
              <option value={availableYear} key={availableYear}>
                {availableYear}
              </option>
            ))}
          </select>
        </div>
        <div className="range-control">
          <div>
            <label htmlFor="observations">Min observed records</label>
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

      <section className="panel-stats" aria-label="Visible data summary">
        <article>
          <span>{summary.gridCells.toLocaleString('en-US')}</span>
          <p>visible grids</p>
        </article>
        <article>
          <span>{METRICS.normalizedRichness.format(summary.averageRichness)}</span>
          <p>avg richness</p>
        </article>
        <article>
          <span>{METRICS.forestCoverPct.format(summary.averageForestCover)}</span>
          <p>avg forest</p>
        </article>
      </section>

      <div className="analysis-scroll">
        <section className="selected-card" aria-label="Selected grid cell">
          <div className="selected-card-title">
            <Crosshair size={17} aria-hidden="true" />
            <h2>Grid information</h2>
          </div>
          {activeRecord ? (
            <>
              <strong>{activeRecord.gridId}</strong>
              <p>
                {formatCoordinate(activeRecord.lat)}, {formatCoordinate(activeRecord.lon)} · {activeRecord.year}
              </p>
              <dl>
                {selectedDetails.map((detail) => (
                  <div key={detail.label}>
                    <dt>{detail.label}</dt>
                    <dd>{detail.value}</dd>
                  </div>
                ))}
              </dl>
              {year !== 2024 && (
                <p className="projection-hint">
                  Switch to 2024 to run a {PROJECTION_YEAR} projection for this grid.
                </p>
              )}
            </>
          ) : (
            <p>
              {year === 2024
                ? 'Click a marker on the map to start single-grid inference.'
                : 'Click a marker on the map to inspect observed history for this year.'}
            </p>
          )}
        </section>

        {year === 2024 && activeRecord && (
          <section className="inference-card" aria-label="Model inference setup">
            <div className="inference-title">
              <div>
                <Crosshair size={17} aria-hidden="true" />
                <h2>Prediction</h2>
              </div>
            </div>
            <label className="model-picker" htmlFor="model-picker">
              <span>Model</span>
              <select
                id="model-picker"
                value={selectedModelId}
                disabled={modelOptionsStatus !== 'ready'}
                onChange={(event) => setSelectedModelId(event.target.value)}
              >
                {modelOptions.map((modelOption) => (
                  <option value={modelOption.model_id} key={modelOption.model_id}>
                    {modelOption.label}
                  </option>
                ))}
              </select>
            </label>
            {modelOptionsStatus === 'error' && <p className="helper">Model metadata API is unavailable.</p>}
            <div className="editable-inputs" aria-label="Editable prediction inputs">
              <div className="editable-inputs-title">
                <span>Input</span>
                <em>{PROJECTION_YEAR}</em>
              </div>
              <div className="scenario-grid">
                <label>
                  <span>Forest cover (%)</span>
                  <input
                    min="0"
                    max="100"
                    step="0.1"
                    type="number"
                    value={scenarioCover ?? ''}
                    onChange={(event) => {
                      setScenarioCover(event.target.value === '' ? null : Number(event.target.value));
                      setScenarioResult(null);
                      setScenarioStatus('idle');
                    }}
                  />
                </label>
                <label>
                  <span>Forest loss (ha)</span>
                  <input
                    min="0"
                    step="0.1"
                    type="number"
                    value={scenarioLoss ?? ''}
                    onChange={(event) => {
                      setScenarioLoss(event.target.value === '' ? null : Number(event.target.value));
                      setScenarioResult(null);
                      setScenarioStatus('idle');
                    }}
                  />
                </label>
              </div>
              <div className="scenario-presets">
                <button type="button" onClick={resetScenario}>
                  Reset inputs
                </button>
              </div>
            </div>
            <button
              className="primary-button inference-button"
              disabled={!canRunInference || gridDetailsStatus === 'loading' || scenarioStatus === 'running'}
              type="button"
              onClick={runInference}
            >
              {gridDetailsStatus === 'loading' || scenarioStatus === 'running'
                ? 'Running prediction...'
                : 'Run prediction'}
            </button>
            {(gridDetailsStatus === 'error' || scenarioStatus === 'error') && (
              <p className="helper scenario-error">Prediction failed.</p>
            )}
          </section>
        )}

        {year === 2024 && activeRecord && gridDetailsStatus !== 'idle' && (
          <section className="prediction-card" aria-label="Prediction result">
            <h2>{PROJECTION_YEAR} prediction result</h2>
            {gridDetailsStatus === 'ready' && gridDetails ? (
              <>
                <p className="card-kicker">{gridDetails.model_label}</p>
                <div className="prediction-main">
                  <span>{(scenarioResult?.scenario_predicted ?? gridDetails.predicted).toFixed(2)} / 1.00</span>
                </div>
              </>
            ) : (
              <p className="helper">
                {gridDetailsStatus === 'error' ? 'Model API is unavailable.' : 'Running model output...'}
              </p>
            )}
          </section>
        )}

        {year === 2024 && activeRecord && gridDetailsStatus !== 'idle' && (
          <section className="explanation-card" aria-label="Feature audit">
            {gridDetailsStatus === 'ready' && gridDetails && isFeatureAuditComplete ? (
              <details className="feature-audit" open>
                <summary>
                  <span>Feature audit</span>
                </summary>
                <p className="audit-note">Δ score compares the current value against the training median.</p>
                <div className="feature-audit-table" role="table" aria-label="All model feature effects">
                  <div className="feature-audit-row feature-audit-head" role="row">
                    <span role="columnheader">Feature</span>
                    <span role="columnheader">Value</span>
                    <span role="columnheader">Median</span>
                    <span role="columnheader">Δ score</span>
                  </div>
                  {featureAuditRows.map((row) => (
                    <div className="feature-audit-row" role="row" key={row.feature_key}>
                      <span className="audit-feature" role="cell">
                        {row.feature_label}
                        <small>{row.feature_key}</small>
                      </span>
                      <span role="cell">{formatAuditValue(row.value, row.feature_key)}</span>
                      <span role="cell">{formatAuditValue(row.reference_value, row.feature_key)}</span>
                      <span className={`audit-delta audit-delta-${row.direction}`} role="cell">
                        {formatScoreDelta(row.contribution)}
                      </span>
                    </div>
                  ))}
                </div>
              </details>
            ) : (
              <p className="helper">
                {gridDetailsStatus === 'error'
                  ? 'Explanation is unavailable.'
                  : gridDetailsStatus === 'ready'
                    ? 'Feature audit needs the latest backend response. Restart FastAPI and run prediction again.'
                    : 'Running explanation...'}
              </p>
            )}
          </section>
        )}

      </div>
    </aside>
  );
}

function detailIfFinite(
  label: string,
  value: number,
  formatter: (value: number) => string,
): { label: string; value: string } | null {
  if (!Number.isFinite(value)) return null;
  return { label, value: formatter(value) };
}

function toNullableNumber(value: number | undefined): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function formatAuditValue(value: number | null, featureKey: string): string {
  if (value === null || !Number.isFinite(value)) return '—';
  if (featureKey === 'lat' || featureKey === 'lon') return `${value.toFixed(2)}°`;
  if (featureKey.includes('pct')) return `${formatNumber(value, 2)}%`;
  if (featureKey.includes('forest_loss_ha')) return `${formatNumber(value, 2)} ha`;
  if (featureKey.includes('years_since')) return `${formatNumber(value, 0)} yr`;
  if (
    featureKey.includes('n_observations') ||
    featureKey.includes('n_species') ||
    featureKey === 'prior_records_for_cell'
  ) {
    return formatNumber(value, 0);
  }
  if (featureKey.startsWith('normalized_richness_01')) return value.toFixed(3);
  return formatNumber(value, 2);
}

function formatScoreDelta(contribution: number): string {
  if (!Number.isFinite(contribution)) return '0.000';
  const sign = contribution > 0 ? '+' : contribution < 0 ? '-' : '';
  return `${sign}${Math.abs(contribution).toFixed(3)}`;
}
