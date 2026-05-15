import type { MetricKey } from '../types';
import { METRICS } from '../utils/biodiversityMetrics';

type MetricLegendProps = {
  metric: MetricKey;
  min: number;
  max: number;
};

export function MetricLegend({ metric, min, max }: MetricLegendProps) {
  const definition = METRICS[metric];

  return (
    <div className="map-legend">
      <div>
        <strong>{definition.shortLabel}</strong>
        <span>{definition.description}</span>
      </div>
      <div className={`legend-ramp legend-ramp--${metric}`} aria-hidden="true" />
      <div className="legend-scale">
        <span>{definition.format(min)}</span>
        <span>{definition.format(max)}</span>
      </div>
      <p>
        Marker size follows latest available
        <br />
        GBIF observation effort.
      </p>
    </div>
  );
}
