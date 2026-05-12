import { useEffect, useMemo } from 'react';
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet';
import type { LatLngBoundsExpression } from 'leaflet';
import type { BiodiversityRecord, MetricKey } from '../types';
import {
  getMetricDomain,
  getMetricValue,
  METRICS,
} from '../utils/biodiversityMetrics';
import { formatCoordinate, formatNumber } from '../utils/formatters';
import { MetricLegend } from './MetricLegend';

const VIETNAM_BOUNDS: LatLngBoundsExpression = [
  [8.0, 102.0],
  [23.6, 110.1],
];
const VIETNAM_CENTER: [number, number] = [16.1, 106.2];

type VietnamMapProps = {
  records: BiodiversityRecord[];
  metric: MetricKey;
  selectedGridId: string | null;
  onSelectRecord: (record: BiodiversityRecord) => void;
};

export function VietnamMap({
  records,
  metric,
  selectedGridId,
  onSelectRecord,
}: VietnamMapProps) {
  const domain = useMemo(() => getMetricDomain(records, metric), [records, metric]);

  return (
    <section className="map-shell" aria-label="Vietnam biodiversity map">
      <MapContainer
        center={VIETNAM_CENTER}
        className="map-canvas"
        maxBounds={VIETNAM_BOUNDS}
        maxBoundsViscosity={0.8}
        minZoom={5}
        preferCanvas
        scrollWheelZoom
        zoom={5.7}
        zoomSnap={0.25}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ResetVietnamView />
        {records.map((record) => (
          <CircleMarker
            center={[record.lat, record.lon]}
            eventHandlers={{
              click: () => onSelectRecord(record),
            }}
            key={`${record.gridId}-${record.year}`}
            pathOptions={{
              color: getMarkerColor(record, metric, domain.min, domain.max),
              fillColor: getMarkerColor(record, metric, domain.min, domain.max),
              fillOpacity: record.gridId === selectedGridId ? 0.95 : 0.7,
              opacity: 0.92,
              weight: record.gridId === selectedGridId ? 3 : 1,
            }}
            radius={record.gridId === selectedGridId ? getMarkerRadius(record) + 3 : getMarkerRadius(record)}
          >
            <Tooltip className="map-tooltip" direction="top" offset={[0, -4]} opacity={0.96}>
              <strong>{record.gridId}</strong>
              <span>
                {formatCoordinate(record.lat)}, {formatCoordinate(record.lon)} · {record.year}
              </span>
              <dl>
                <div>
                  <dt>{METRICS.normalizedRichness.shortLabel}</dt>
                  <dd>{METRICS.normalizedRichness.format(record.normalizedRichness)}</dd>
                </div>
                <div>
                  <dt>Species</dt>
                  <dd>{formatNumber(record.nSpecies)}</dd>
                </div>
                <div>
                  <dt>Observations</dt>
                  <dd>{formatNumber(record.nObservations)}</dd>
                </div>
                <div>
                  <dt>Forest loss</dt>
                  <dd>{METRICS.forestLossHa.format(record.forestLossHa)}</dd>
                </div>
                <div>
                  <dt>Rainfall</dt>
                  <dd>{METRICS.totalRainfallMm.format(record.totalRainfallMm)}</dd>
                </div>
              </dl>
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
      <MetricLegend metric={metric} min={domain.min} max={domain.max} />
    </section>
  );
}

function ResetVietnamView() {
  const map = useMap();

  useEffect(() => {
    map.setView(VIETNAM_CENTER, 5.7);
  }, [map]);

  return null;
}

function getMarkerRadius(record: BiodiversityRecord): number {
  const effort = Math.log1p(record.nObservations);
  return Math.max(4.5, Math.min(18, 3.5 + effort * 1.25));
}

function getMarkerColor(
  record: BiodiversityRecord,
  metric: MetricKey,
  min: number,
  max: number,
): string {
  const value = getMetricValue(record, metric);
  if (!Number.isFinite(value)) return '#94a3b8';

  const progress = max === min ? 0.5 : Math.min(1, Math.max(0, (value - min) / (max - min)));
  const palette = METRICS[metric].palette;

  if (progress <= 0.5) {
    return interpolateHex(palette[0], palette[1], progress * 2);
  }
  return interpolateHex(palette[1], palette[2], (progress - 0.5) * 2);
}

function interpolateHex(from: string, to: string, amount: number): string {
  const fromRgb = hexToRgb(from);
  const toRgb = hexToRgb(to);
  const mixed = fromRgb.map((channel, index) =>
    Math.round(channel + (toRgb[index] - channel) * amount),
  );

  return `rgb(${mixed[0]}, ${mixed[1]}, ${mixed[2]})`;
}

function hexToRgb(hex: string): [number, number, number] {
  const value = hex.replace('#', '');
  return [
    Number.parseInt(value.slice(0, 2), 16),
    Number.parseInt(value.slice(2, 4), 16),
    Number.parseInt(value.slice(4, 6), 16),
  ];
}
