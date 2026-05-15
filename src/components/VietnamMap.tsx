import { useEffect, useMemo, useState } from 'react';
import { Circle, LayerGroup, MapContainer, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet';
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
  const [zoom, setZoom] = useState(5.7);
  const renderOrder = useMemo(() => {
    const sortedRecords = records.slice().sort((left, right) => {
      const byObservations = left.nObservations - right.nObservations;
      if (byObservations !== 0) return byObservations;
      return left.gridId.localeCompare(right.gridId);
    });

    const selectedRecordIndex = selectedGridId
      ? sortedRecords.findIndex((record) => record.gridId === selectedGridId)
      : -1;

    if (selectedRecordIndex === -1) {
      return {
        orderedUnselected: sortedRecords,
        selectedRecord: null as BiodiversityRecord | null,
      };
    }

    const [selectedRecord] = sortedRecords.splice(selectedRecordIndex, 1);
    return { orderedUnselected: sortedRecords, selectedRecord };
  }, [records, selectedGridId]);

  const orderedUnselected = renderOrder.orderedUnselected;
  const selectedRecord = renderOrder.selectedRecord;

  const markersEpoch = useMemo(() => hashRecordsForRenderKey(records), [records]);

  return (
    <section className="map-shell" aria-label="Vietnam biodiversity map">
      <MapContainer
        center={VIETNAM_CENTER}
        className="map-canvas"
        minZoom={5}
        preferCanvas
        scrollWheelZoom={true}
        zoom={5.7}
        zoomSnap={0.25}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ResetVietnamView />
        <FlyToSelection record={selectedRecord} />
        <ZoomTracker onZoomEnd={setZoom} />
        <LayerGroup key={`markers-${markersEpoch}`}>
          {orderedUnselected.map((record) =>
            renderGridMarker(record, false, metric, domain.min, domain.max, zoom, onSelectRecord),
          )}
        </LayerGroup>
        {selectedRecord && (
          <LayerGroup key={`selected-${selectedRecord.gridId}-${selectedRecord.year}`}>
            {renderGridMarker(selectedRecord, true, metric, domain.min, domain.max, zoom, onSelectRecord)}
          </LayerGroup>
        )}
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

function FlyToSelection({ record }: { record: BiodiversityRecord | null }) {
  const map = useMap();
  const selectedGridId = record?.gridId ?? null;

  useEffect(() => {
    if (!record) return;

    const currentZoom = map.getZoom();
    const nextZoom = Math.max(currentZoom, 8.75);

    map.flyTo([record.lat, record.lon], nextZoom, { animate: true, duration: 0.8 });
  }, [map, record, selectedGridId]);

  return null;
}

function ZoomTracker({ onZoomEnd }: { onZoomEnd: (zoom: number) => void }) {
  const map = useMapEvents({
    zoomend: () => {
      onZoomEnd(map.getZoom());
    },
  });

  useEffect(() => {
    onZoomEnd(map.getZoom());
  }, [map, onZoomEnd]);

  return null;
}

function hashRecordsForRenderKey(records: BiodiversityRecord[]) {
  let hash = 0;
  for (const record of records) {
    const key = `${record.gridId}:${record.year}:${record.nObservations}`;
    for (let index = 0; index < key.length; index += 1) {
      hash = (hash * 31 + key.charCodeAt(index)) | 0;
    }
  }
  return `${records.length}-${Math.abs(hash)}`;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function lerp(from: number, to: number, progress: number) {
  return from + (to - from) * progress;
}

function metersPerPixel(latitude: number, zoom: number) {
  const latitudeRadians = (latitude * Math.PI) / 180;
  return (156543.03392 * Math.cos(latitudeRadians)) / Math.pow(2, zoom);
}

function getMarkerRadiusMeters(record: BiodiversityRecord, zoom: number): number {
  const effort = Math.log1p(record.nObservations);
  const effortScale = clamp(0.7 + effort * 0.07, 0.6, 1.28);
  const effortProgress = clamp((effortScale - 0.6) / (1.28 - 0.6), 0, 1);
  const desiredMeters = 4200 * effortScale;

  const zoomProgress = clamp((zoom - 6) / 3, 0, 1);
  const minPixelRadius = lerp(3.0, 5.5, zoomProgress) * lerp(0.95, 1.35, effortProgress);
  const maxPixelRadius = lerp(20, 32, zoomProgress) * lerp(0.9, 1.45, effortProgress);

  const pixelToMeters = metersPerPixel(record.lat, zoom);
  const minMeters = minPixelRadius * pixelToMeters;
  const maxMeters = maxPixelRadius * pixelToMeters;

  return clamp(desiredMeters, minMeters, maxMeters);
}

function renderGridMarker(
  record: BiodiversityRecord,
  isSelected: boolean,
  metric: MetricKey,
  min: number,
  max: number,
  zoom: number,
  onSelectRecord: (record: BiodiversityRecord) => void,
) {
  const markerColor = getMarkerColor(record, metric, min, max);
  const radius = getMarkerRadiusMeters(record, zoom) * (isSelected ? 1.18 : 1);
  return (
    <Circle
      className={isSelected ? 'selected-grid-marker' : undefined}
      center={[record.lat, record.lon]}
      eventHandlers={{
        click: () => onSelectRecord(record),
      }}
      key={`${record.gridId}-${record.year}${isSelected ? '-selected' : ''}`}
      pathOptions={{
        color: isSelected ? '#052e22' : markerColor,
        fillColor: markerColor,
        fillOpacity: isSelected ? 0.92 : 0.7,
        opacity: isSelected ? 1 : 0.88,
        weight: isSelected ? 3 : 1,
      }}
      radius={radius}
    >
      <Tooltip className="map-tooltip" direction="top" offset={[0, -4]} opacity={0.96}>
        <strong>{record.gridId}</strong>
        <span>
          {formatCoordinate(record.lat)}, {formatCoordinate(record.lon)} · {record.year}
        </span>
        <dl>
          <div>
            <dt>{METRICS[metric].shortLabel}</dt>
            <dd>{METRICS[metric].format(record[metric])}</dd>
          </div>
          {metric !== 'normalizedRichness' && (
            <div>
              <dt>{METRICS.normalizedRichness.shortLabel}</dt>
              <dd>{METRICS.normalizedRichness.format(record.normalizedRichness)}</dd>
            </div>
          )}
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
        </dl>
      </Tooltip>
    </Circle>
  );
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
