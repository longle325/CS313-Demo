const numberFormatter = new Intl.NumberFormat('en-US');
const compactFormatter = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

export function formatNumber(value: number, maximumFractionDigits = 0): string {
  if (!Number.isFinite(value)) return 'N/A';

  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits,
  }).format(value);
}

export function formatCompact(value: number): string {
  if (!Number.isFinite(value)) return 'N/A';

  return compactFormatter.format(value);
}

export function formatInteger(value: number): string {
  if (!Number.isFinite(value)) return 'N/A';

  return numberFormatter.format(Math.round(value));
}

export function formatCoordinate(value: number): string {
  if (!Number.isFinite(value)) return 'N/A';

  return `${value.toFixed(2)}°`;
}
