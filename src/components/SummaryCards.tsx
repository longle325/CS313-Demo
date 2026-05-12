import { Activity, Binoculars, Leaf, MapPinned, Sprout } from 'lucide-react';
import type { DatasetSummary } from '../types';
import { formatCompact, formatCoordinate, formatNumber } from '../utils/formatters';

type SummaryCardsProps = {
  summary: DatasetSummary;
};

export function SummaryCards({ summary }: SummaryCardsProps) {
  const topGridLabel = summary.topGrid
    ? `${formatCoordinate(summary.topGrid.lat)}, ${formatCoordinate(summary.topGrid.lon)}`
    : 'No grid selected';

  const cards = [
    {
      label: 'Grid-year records',
      value: formatNumber(summary.totalRows),
      detail: `${formatNumber(summary.gridCells)} grid cells`,
      icon: MapPinned,
    },
    {
      label: 'GBIF observations',
      value: formatCompact(summary.totalObservations),
      detail: 'Citizen-science records',
      icon: Binoculars,
    },
    {
      label: 'Species-cell total',
      value: formatCompact(summary.speciesCellCount),
      detail: 'Summed per grid-year, not unique taxa',
      icon: Sprout,
    },
    {
      label: 'Mean richness',
      value: formatNumber(summary.averageRichness, 2),
      detail: 'n_species / log(1 + observations)',
      icon: Activity,
    },
    {
      label: 'Top richness grid',
      value: summary.topGrid ? formatNumber(summary.topGrid.normalizedRichness, 2) : '—',
      detail: topGridLabel,
      icon: Leaf,
    },
  ];

  return (
    <section className="summary-grid" aria-label="Dataset summary">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <article className="summary-card" key={card.label}>
            <div className="summary-icon" aria-hidden="true">
              <Icon size={18} strokeWidth={2} />
            </div>
            <div>
              <p>{card.label}</p>
              <strong>{card.value}</strong>
              <span>{card.detail}</span>
            </div>
          </article>
        );
      })}
    </section>
  );
}
