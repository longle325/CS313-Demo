import { useEffect, useMemo, useState } from 'react';
import { Circle, MapContainer, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet';
import type { LatLngBoundsExpression } from 'leaflet';
import type { BiodiversityRecord, MetricKey } from '../types';
import {
  getMetricDomain,
  getMetricValue,
  METRICS,
} from '../utils/biodiversityMetrics';
import { formatCoordinate, formatNumber } from '../utils/formatters';
import { MetricLegend } from './MetricLegend';

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
  const markersKey = useMemo(() => getMarkersKey(records), [records]);
  const selectedRecord = useMemo(
    () => records.find((record) => record.gridId === selectedGridId) ?? null,
    [records, selectedGridId],
  );

  return (
    <section className="map-shell" aria-label="Vietnam biodiversity map">
      <MapContainer
        center={VIETNAM_CENTER}
        className="map-canvas"
        minZoom={5}
        scrollWheelZoom
        zoom={5.7}
        zoomSnap={0.25}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FocusSelectedRecord selectedRecord={selectedRecord} />
        <MarkersLayer
          key={markersKey}
          records={records}
          metric={metric}
          metricMin={domain.min}
          metricMax={domain.max}
          selectedGridId={selectedGridId}
          onSelectRecord={onSelectRecord}
        />
      </MapContainer>
      <MetricLegend metric={metric} min={domain.min} max={domain.max} />
    </section>
  );
}

type MarkersLayerProps = {
  records: BiodiversityRecord[];
  metric: MetricKey;
  metricMin: number;
  metricMax: number;
  selectedGridId: string | null;
  onSelectRecord: (record: BiodiversityRecord) => void;
};

function MarkersLayer({
  records,
  metric,
  metricMin,
  metricMax,
  selectedGridId,
  onSelectRecord,
}: MarkersLayerProps) {
  const map = useMap();
  const [zoom, setZoom] = useState(() => map.getZoom());
  const sortedRecords = useMemo(() => {
    const ordered = records
      .slice()
      .sort((a, b) => a.nObservations - b.nObservations || a.gridId.localeCompare(b.gridId));

    if (!selectedGridId) return ordered;
    const selectedIndex = ordered.findIndex((record) => record.gridId === selectedGridId);
    if (selectedIndex === -1) return ordered;

    const [selected] = ordered.splice(selectedIndex, 1);
    ordered.push(selected);
    return ordered;
  }, [records, selectedGridId]);

  useMapEvents({
    zoomend: (event) => setZoom(event.target.getZoom()),
  });

  return sortedRecords.map((record) => {
    const isSelected = record.gridId === selectedGridId;
    const radius = getMarkerRadiusMeters(record, zoom);
    const id = `${record.gridId}-${record.year}`;
    const markerColor = getMarkerColor(record, metric, metricMin, metricMax);

    return (
      <Circle
        center={[record.lat, record.lon]}
        eventHandlers={{
          click: () => onSelectRecord(record),
        }}
        key={id}
        pathOptions={{
          color: isSelected ? '#0f172a' : markerColor,
          fillColor: markerColor,
          fillOpacity: isSelected ? 0.95 : 0.7,
          opacity: 0.92,
          weight: isSelected ? 4 : 1,
        }}
        radius={isSelected ? radius * 1.18 : radius}
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
      </Circle>
    );
  });
}

type FocusSelectedRecordProps = {
  selectedRecord: BiodiversityRecord | null;
};

function FocusSelectedRecord({ selectedRecord }: FocusSelectedRecordProps) {
  const map = useMap();

  useEffect(() => {
    if (!selectedRecord) return;

    const nextZoom = Math.max(map.getZoom(), 8.75);
    map.flyTo([selectedRecord.lat, selectedRecord.lon], nextZoom, {
      animate: true,
      duration: 0.8,
    });
  }, [map, selectedRecord]);

  return null;
}

function getMarkerRadiusMeters(record: BiodiversityRecord, zoom: number): number {
  const metersPerPixel = getMetersPerPixel(record.lat, zoom);
  const effort = Math.log1p(record.nObservations);
  const effortScale = clamp(0.7 + effort * 0.06, 0.6, 1.22);
  const desiredMeters = 4200 * effortScale;
  const effortProgress = clamp((effortScale - 0.6) / (1.22 - 0.6), 0, 1);

  const zoomProgress = clamp((zoom - 6) / 3, 0, 1);
  const minPixelRadius =
    lerp(2.7, 5.5, zoomProgress) * lerp(0.95, 1.35, effortProgress);
  const maxPixelRadius =
    lerp(18, 32, zoomProgress) * lerp(0.9, 1.45, effortProgress);
  const minMeters = minPixelRadius * metersPerPixel;
  const maxMeters = maxPixelRadius * metersPerPixel;

  return clamp(desiredMeters, minMeters, maxMeters);
}

function getMetersPerPixel(latitude: number, zoom: number): number {
  const latitudeFactor = Math.cos((latitude * Math.PI) / 180);
  return (156543.03392 * latitudeFactor) / Math.pow(2, zoom);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function lerp(from: number, to: number, amount: number): number {
  return from + (to - from) * amount;
}

function getMarkersKey(records: BiodiversityRecord[]): string {
  let hash = 2166136261;
  for (const record of records) {
    const id = `${record.gridId}-${record.year}-${record.nObservations}`;
    for (let index = 0; index < id.length; index += 1) {
      hash ^= id.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
  }
  return `${records.length}-${hash >>> 0}`;
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
