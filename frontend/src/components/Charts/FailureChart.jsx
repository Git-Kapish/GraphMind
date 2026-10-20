import React from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { getStackedBarChartConfig, chartColors, chartColorsDark } from '../../utils/chartTheme';
import { useColorScheme } from '../../hooks/useReducedMotion';
import { GlassPanel } from '../ui/Card';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export function FailureChart({ data }) {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';
  const c = isDark ? chartColorsDark : chartColors;

  const errorTypes = [
    { key: 'retrievalMiss', label: 'Retrieval Miss', color: c.red },
    { key: 'generationError', label: 'Generation Error', color: c.orange },
    { key: 'refusalError', label: 'Refusal Error', color: c.purple },
    { key: 'routerError', label: 'Router Error', color: c.pink },
  ];

  const chartData = {
    labels: data.failureTaxonomy.map(f => f.system),
    datasets: errorTypes.map((type, i) => ({
      label: type.label,
      data: data.failureTaxonomy.map(f => f[type.key] || 0),
      backgroundColor: type.color,
      borderColor: type.color,
      borderWidth: 0,
      borderRadius: i === 0 ? { topLeft: 4, bottomLeft: 4 } : i === errorTypes.length - 1 ? { topRight: 4, bottomRight: 4 } : 0,
      borderSkipped: false,
    })),
  };

  const options = getStackedBarChartConfig(isDark).options;

  return (
    <GlassPanel padding="lg">
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <h3 style={{ margin: '0 0 var(--space-1)', fontSize: 'var(--text-lg)', fontWeight: 600 }}>
          Failure Taxonomy & Root Cause Analysis
        </h3>
        <p style={{ margin: 0, fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)' }}>
          Breakdown of error types per system (PRD FR-5.2). Stacked horizontal bars.
        </p>
      </div>
      <div style={{ height: '280px', position: 'relative' }}>
        <Bar
          data={chartData}
          options={{
            ...options,
            indexAxis: 'y',
            plugins: {
              ...options.plugins,
              tooltip: {
                ...options.plugins.tooltip,
                callbacks: {
                  label: (context) => {
                    const item = data.failureTaxonomy[context.dataIndex];
                    const type = errorTypes.find(t => t.key === context.dataset.label);
                    return [
                      `${type?.label || context.dataset.label}: ${context.parsed.x}`,
                      `Total Errors: ${item.totalErrors}`,
                      item.notes && `Notes: ${item.notes}`,
                    ].filter(Boolean);
                  },
                },
              },
            },
          }}
        />
      </div>

      {/* Summary table */}
      <div style={{ marginTop: 'var(--space-4)', overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-sm)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--glass-border)' }}>
              <th style={{ textAlign: 'left', padding: 'var(--space-2) var(--space-3)', color: 'var(--fg-tertiary)', fontWeight: 500, fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>System</th>
              <th style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', color: 'var(--fg-tertiary)', fontWeight: 500, fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>Retrieval Miss</th>
              <th style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', color: 'var(--fg-tertiary)', fontWeight: 500, fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>Generation Error</th>
              <th style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', color: 'var(--fg-tertiary)', fontWeight: 500, fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>Refusal Error</th>
              <th style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', color: 'var(--fg-tertiary)', fontWeight: 500, fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>Router Error</th>
              <th style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', color: 'var(--fg-tertiary)', fontWeight: 500, fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>Total</th>
            </tr>
          </thead>
          <tbody>
            {data.failureTaxonomy.map((f, idx) => (
              <tr key={f.system} style={{ borderBottom: idx < data.failureTaxonomy.length - 1 ? '1px solid var(--glass-border)' : 'none' }}>
                <td style={{ padding: 'var(--space-2) var(--space-3)', fontWeight: 600, color: f.isPrimary ? 'var(--accent-green)' : 'var(--fg-primary)' }}>
                  {f.name}
                </td>
                <td style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', fontFamily: 'var(--font-mono)', color: f.retrievalMiss > 0 ? 'var(--accent-red)' : 'var(--fg-secondary)' }}>{f.retrievalMiss}</td>
                <td style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', fontFamily: 'var(--font-mono)', color: f.generationError > 0 ? 'var(--accent-orange)' : 'var(--fg-secondary)' }}>{f.generationError}</td>
                <td style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', fontFamily: 'var(--font-mono)', color: f.refusalError > 0 ? 'var(--accent-purple)' : 'var(--fg-secondary)' }}>{f.refusalError}</td>
                <td style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', fontFamily: 'var(--font-mono)', color: f.routerError > 0 ? 'var(--accent-pink)' : 'var(--fg-secondary)' }}>{f.routerError}</td>
                <td style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--fg-primary)' }}>
                  {f.totalErrors}
                  {f.isPrimary && <span style={{ marginLeft: 'var(--space-2)', fontSize: 'var(--text-xs)', color: 'var(--accent-green)' }}>★</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </GlassPanel>
  );
}