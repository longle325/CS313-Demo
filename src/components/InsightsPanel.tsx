import { useEffect, useState } from 'react';
import { Crosshair, RotateCcw, Sprout } from 'lucide-react';
import { api, type ApiGridResponse, type ApiModelOption, type ApiScenarioResponse } from '../data/apiClient';
import type { BiodiversityRecord, DatasetSummary, MetricKey } from '../types';
import { METRICS } from '../utils/biodiversityMetrics';
import { formatCoordinate, formatNumber } from '../utils/formatters';

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
  const selectedModel = modelOptions.find((modelOption) => modelOption.model_id === selectedModelId) ?? null;
  const canRunInference =
    year >= 2024 && activeRecord !== null && selectedModelId !== '' && modelOptionsStatus === 'ready';
  const baselineCover = gridDetails?.features.find((feature) => feature.key === 'forest_cover_pct')?.value ?? null;
  const baselineLoss = gridDetails?.features.find((feature) => feature.key === 'forest_loss_ha')?.value ?? null;
  const modelFeatureDetails = gridDetails?.features.filter((feature) => feature.value !== null) ?? [];
  const maxContribution =
    gridDetails?.explanation.reduce(
      (currentMax, row) => Math.max(currentMax, Math.abs(row.contribution)),
      0,
    ) ?? 0;
  const totalContributionImpact =
    gridDetails?.explanation.reduce(
      (total, row) => total + Math.abs(row.contribution),
      0,
    ) ?? 0;

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
    setScenarioCover(null);
    setScenarioLoss(null);
    setScenarioResult(null);
    setScenarioStatus('idle');
  }, [activeRecord?.gridId, selectedModelId, year]);

  useEffect(() => {
    if (!gridDetails || year < 2024) return;
    const cover = gridDetails.features.find((feature) => feature.key === 'forest_cover_pct')?.value;
    const loss = gridDetails.features.find((feature) => feature.key === 'forest_loss_ha')?.value;
    setScenarioCover(cover ?? null);
    setScenarioLoss(loss ?? null);
    setScenarioResult(null);
    setScenarioStatus('idle');
  }, [gridDetails?.grid_id, year]);

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

  function runScenario() {
    if (!gridDetails || scenarioCover === null || scenarioLoss === null) return;

    setScenarioStatus('running');
    api
      .scenario({
        grid_id: gridDetails.grid_id,
        year: gridDetails.year as 2024 | 2025,
        model_id: gridDetails.model_id,
        forest_cover_pct: scenarioCover,
        forest_loss_ha: scenarioLoss,
      })
      .then((result) => {
        setScenarioResult(result);
        setScenarioStatus('ready');
      })
      .catch(() => {
        setScenarioStatus('error');
      });
  }

  function runInference() {
    if (!activeRecord || !selectedModelId) return;

    setGridDetails(null);
    setGridDetailsStatus('loading');
    setScenarioResult(null);
    setScenarioStatus('idle');
    api
      .grid(activeRecord.gridId, year, selectedModelId)
      .then((data) => {
        setGridDetails(data);
        setGridDetailsStatus('ready');
      })
      .catch(() => {
        setGridDetails(null);
        setGridDetailsStatus('error');
      });
  }

  function applyStressScenario() {
    if (baselineCover === null || baselineLoss === null) return;
    setScenarioCover(Math.max(0, Number((baselineCover - 30).toFixed(1))));
    setScenarioLoss(Number((baselineLoss + 200).toFixed(1)));
    setScenarioResult(null);
    setScenarioStatus('idle');
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
              {year >= 2024 && modelFeatureDetails.length > 0 && (
                <div className="model-feature-strip" aria-label="Model feature snapshot">
                  <p>Model feature snapshot</p>
                  {modelFeatureDetails.map((feature) => (
                    <span key={feature.key}>
                      <strong>{feature.label}</strong>
                      {formatFeatureValue(feature.value, feature.unit)}
                    </span>
                  ))}
                </div>
              )}
              {year > 2024 && (
                <p className="projection-note">
                  Projection year: future rows keep the latest known 2024 grid context unless the scenario controls
                  below modify forest cover or loss.
                </p>
              )}
            </>
          ) : (
            <p>Click a marker on the map to start single-grid inference.</p>
          )}
        </section>

        {year >= 2024 && activeRecord && (
          <section className="inference-card" aria-label="Model inference setup">
            <div className="inference-title">
              <div>
                <Crosshair size={17} aria-hidden="true" />
                <h2>Model inference</h2>
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
                    {modelOption.test_r2 === null ? '' : ` · R² ${modelOption.test_r2.toFixed(3)}`}
                  </option>
                ))}
              </select>
            </label>
            {selectedModel && (
              <div className="model-metrics" aria-label="Selected model leaderboard metrics">
                <span>{selectedModel.family}</span>
                <span>Valid R² {formatOptionalMetric(selectedModel.valid_r2)}</span>
                <span>Test R² {formatOptionalMetric(selectedModel.test_r2)}</span>
                <span>MAE {formatOptionalMetric(selectedModel.mae)}</span>
              </div>
            )}
            {modelOptionsStatus === 'error' && <p className="helper">Model metadata API is unavailable.</p>}
            <button
              className="primary-button inference-button"
              disabled={!canRunInference || gridDetailsStatus === 'loading'}
              type="button"
              onClick={runInference}
            >
              {gridDetailsStatus === 'loading' ? 'Running inference...' : `Run inference for ${year}`}
            </button>
            {gridDetailsStatus === 'error' && <p className="helper scenario-error">Inference failed.</p>}
          </section>
        )}

        {year >= 2024 && activeRecord && gridDetailsStatus !== 'idle' && (
          <section className="prediction-card" aria-label="Prediction result">
            <h2>Prediction result</h2>
            {gridDetailsStatus === 'ready' && gridDetails ? (
              <>
                <p className="card-kicker">{gridDetails.model_label}</p>
                <div className="prediction-main">
                  <span>{gridDetails.predicted.toFixed(2)} / 1.00</span>
                  <em className={`level-pill level-${gridDetails.level.toLowerCase()}`}>
                    {gridDetails.level}
                  </em>
                </div>
                <p className="helper">
                  Relative biodiversity index for {gridDetails.year}. Low/Medium/High uses predicted-score
                  percentiles, not absolute biological thresholds.
                </p>
                <div className="threshold-note">
                  <span>p33 {gridDetails.thresholds.p33.toFixed(2)}</span>
                  <span>p66 {gridDetails.thresholds.p66.toFixed(2)}</span>
                  <span>data-driven labels</span>
                </div>
                <dl className="mini-metrics">
                  <div>
                    <dt>{gridDetails.year === 2024 ? 'Observed 2024' : 'Observed target'}</dt>
                    <dd>
                      {gridDetails.observed === null
                        ? gridDetails.year > 2024
                          ? '— projection'
                          : '—'
                        : formatNumber(gridDetails.observed, 2)}
                    </dd>
                  </div>
                  <div>
                    <dt>Residual</dt>
                    <dd>
                      {gridDetails.observed === null
                        ? '—'
                        : `${gridDetails.observed - gridDetails.predicted > 0 ? '+' : ''}${formatNumber(
                            gridDetails.observed - gridDetails.predicted,
                            2,
                          )}`}
                    </dd>
                  </div>
                </dl>
              </>
            ) : (
              <p className="helper">
                {gridDetailsStatus === 'error' ? 'Model API is unavailable.' : 'Running model output...'}
              </p>
            )}
          </section>
        )}

        {year >= 2024 && activeRecord && gridDetailsStatus !== 'idle' && (
          <section className="explanation-card" aria-label="Feature contributions">
            <h2>Top model factors</h2>
            {gridDetailsStatus === 'ready' && gridDetails ? (
              <>
                <p className="helper">
                  Bars show model-agnostic local sensitivity: how the prediction changes if one feature is replaced by
                  its training median. Percent values are relative impact shares among the factors shown, not score
                  increases.
                </p>
                <ol className="explanation-list">
                  {gridDetails.explanation.map((row) => (
                    <li className={`impact impact-${row.direction}`} key={row.feature_key}>
                      <div>
                        <span>{row.feature_label}</span>
                        <em>
                          {impactLabel(row.direction)} · {impactShare(row.contribution, totalContributionImpact)}%
                          impact share
                        </em>
                      </div>
                      <span className="impact-track" aria-hidden="true">
                        <span
                          style={{
                            width: `${impactWidth(row.contribution, maxContribution)}%`,
                          }}
                        />
                      </span>
                    </li>
                  ))}
                </ol>
              </>
            ) : (
              <p className="helper">
                {gridDetailsStatus === 'error' ? 'Explanation is unavailable.' : 'Running explanation...'}
              </p>
            )}
          </section>
        )}

        {year >= 2024 && activeRecord && gridDetailsStatus === 'ready' && gridDetails && (
          <section className="scenario-card" aria-label="Scenario simulation">
            <div className="scenario-title">
              <div>
                <Sprout size={17} aria-hidden="true" />
                <h2>Scenario simulation</h2>
              </div>
              <span>forest-only</span>
            </div>
            <p className="helper">
              Change forest cover/loss while all other model features stay fixed for the selected grid.
            </p>
            <div className="scenario-presets">
              <button type="button" onClick={applyStressScenario}>
                Apply degradation scenario
              </button>
              <button type="button" onClick={resetScenario}>
                Reset selected grid
              </button>
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
                  onChange={(event) =>
                    setScenarioCover(event.target.value === '' ? null : Number(event.target.value))
                  }
                />
              </label>
              <label>
                <span>Forest loss (ha)</span>
                <input
                  min="0"
                  step="0.1"
                  type="number"
                  value={scenarioLoss ?? ''}
                  onChange={(event) =>
                    setScenarioLoss(event.target.value === '' ? null : Number(event.target.value))
                  }
                />
              </label>
            </div>
            <button
              className="primary-button"
              disabled={scenarioCover === null || scenarioLoss === null || scenarioStatus === 'running'}
              type="button"
              onClick={runScenario}
            >
              {scenarioStatus === 'running' ? 'Running...' : 'Run scenario prediction'}
            </button>
            {scenarioStatus === 'error' && <p className="helper scenario-error">Scenario failed.</p>}
            {scenarioResult && (
              <div className="scenario-result">
                <div>
                  <span>Original</span>
                  <strong>{scenarioResult.baseline_predicted.toFixed(2)}</strong>
                </div>
                <div>
                  <span>Scenario</span>
                  <strong>{scenarioResult.scenario_predicted.toFixed(2)}</strong>
                </div>
                <div>
                  <span>Change</span>
                  <strong className={scenarioResult.delta < 0 ? 'delta-negative' : 'delta-positive'}>
                    {scenarioResult.delta >= 0 ? '+' : ''}
                    {scenarioResult.delta.toFixed(2)}
                  </strong>
                </div>
              </div>
            )}
            {scenarioResult && (
              <p className="scenario-interpretation">
                {scenarioResult.delta < 0
                  ? 'Interpretation: lower forest cover and higher loss reduce the predicted richness index.'
                  : 'Interpretation: this scenario does not reduce the predicted richness index for this grid.'}
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

function formatFeatureValue(value: number | null, unit?: string | null): string {
  if (value === null || !Number.isFinite(value)) return '—';
  if (unit === '%') return `${formatNumber(value, 1)}%`;
  if (unit === 'ha') return `${formatNumber(value, 1)} ha`;
  if (unit === 'years') return `${formatNumber(value, 0)} years`;
  return formatNumber(value, 2);
}

function impactWidth(contribution: number, maxContribution: number): number {
  if (!Number.isFinite(maxContribution) || maxContribution <= 0) return 8;
  return Math.max(8, (Math.abs(contribution) / maxContribution) * 100);
}

function impactShare(contribution: number, totalContributionImpact: number): string {
  if (!Number.isFinite(totalContributionImpact) || totalContributionImpact <= 0) return '0';
  return formatNumber((Math.abs(contribution) / totalContributionImpact) * 100, 0);
}

function impactLabel(direction: 'positive' | 'negative' | 'neutral'): string {
  if (direction === 'positive') return 'Positive';
  if (direction === 'negative') return 'Negative';
  return 'Neutral';
}

function formatOptionalMetric(value: number | null): string {
  return value === null ? '—' : formatNumber(value, 3);
}
