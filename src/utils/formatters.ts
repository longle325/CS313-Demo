const numberFormatter = new Intl.NumberFormat('en-US');
const compactFormatter = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

export function formatNumber(value: number, maximumFractionDigits = 0): string {
  if (!Number.isFinite(value)) return '—';

  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits,
  }).format(value);
}

export function formatCompact(value: number): string {
  if (!Number.isFinite(value)) return '—';

  return compactFormatter.format(value);
}

export function formatInteger(value: number): string {
  if (!Number.isFinite(value)) return '—';

  return numberFormatter.format(Math.round(value));
}

export function formatCoordinate(value: number): string {
  if (!Number.isFinite(value)) return '—';

  return `${value.toFixed(2)}°`;
}
