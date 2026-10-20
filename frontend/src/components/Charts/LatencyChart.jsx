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
import { getGroupedBarChartConfig, chartColors, chartColorsDark } from '../../utils/chartTheme';
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

export function LatencyChart({ data }) {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';
  const c = isDark ? chartColorsDark : chartColors;

  const chartData = {
    labels: data.systems.map(s => s.id),
    datasets: [
      {
        label: 'p50 Latency (ms)',
        data: data.systems.map(s => s.latency.p50),
        backgroundColor: c.blue,
        borderColor: c.blue,
        borderWidth: 0,
        borderRadius: 4,
        borderSkipped: false,
        maxBarThickness: 40,
      },
      {
        label: 'p95 Latency (ms)',
        data: data.systems.map(s => s.latency.p95),
        backgroundColor: c.orange,
        borderColor: c.orange,
        borderWidth: 0,
        borderRadius: 4,
        borderSkipped: false,
        maxBarThickness: 40,
      },
    ],
  };

  const options = getGroupedBarChartConfig(isDark).options;

  return (
    <GlassPanel padding="lg">
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <h3 style={{ margin: '0 0 var(--space-1)', fontSize: 'var(--text-lg)', fontWeight: 600 }}>
          Latency Comparison (p50 / p95)
        </h3>
        <p style={{ margin: 0, fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)' }}>
          Median and 95th percentile latency in milliseconds. Lower is better.
        </p>
      </div>
      <div style={{ height: '300px', position: 'relative' }}>
        <Bar
          data={chartData}
          options={{
            ...options,
            plugins: {
              ...options.plugins,
              legend: {
                display: true,
                position: 'top',
                align: 'start',
                labels: {
                  usePointStyle: true,
                  pointStyle: 'circle',
                  padding: 16,
                  font: {
                    family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif',
                    size: 12,
                    weight: 500,
                  },
                  color: c.secondary,
                },
              },
              tooltip: {
                ...options.plugins.tooltip,
                callbacks: {
                  label: (context) => {
                    const sys = data.systems[context.dataIndex];
                    const label = context.dataset.label;
                    const value = context.parsed.y;
                    return [
                      `${label}: ${(value / 1000).toFixed(1)}s (${value} ms)`,
                      `Accuracy: ${sys.accuracy}%`,
                    ];
                  },
                },
              },
            },
            scales: {
              ...options.scales,
              x: {
                ...options.scales.x,
                title: {
                  display: true,
                  text: 'System',
                  font: { size: 13, weight: 500 },
                  color: c.secondary,
                },
              },
              y: {
                ...options.scales.y,
                beginAtZero: true,
                title: {
                  display: true,
                  text: 'Latency (ms)',
                  font: { size: 13, weight: 500 },
                  color: c.secondary,
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
              <th style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', color: 'var(--fg-tertiary)', fontWeight: 500, fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>p50 (ms)</th>
              <th style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', color: 'var(--fg-tertiary)', fontWeight: 500, fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>p95 (ms)</th>
              <th style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', color: 'var(--fg-tertiary)', fontWeight: 500, fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>p50 (s)</th>
              <th style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', color: 'var(--fg-tertiary)', fontWeight: 500, fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>p95 (s)</th>
              <th style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', color: 'var(--fg-tertiary)', fontWeight: 500, fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>Accuracy</th>
            </tr>
          </thead>
          <tbody>
            {data.systems.map((s, idx) => (
              <tr key={s.id} style={{ borderBottom: idx < data.systems.length - 1 ? '1px solid var(--glass-border)' : 'none' }}>
                <td style={{ padding: 'var(--space-2) var(--space-3)', fontWeight: 600, color: s.isPrimary ? 'var(--accent-green)' : 'var(--fg-primary)' }}>
                  {s.name}
                </td>
                <td style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', fontFamily: 'var(--font-mono)', color: 'var(--fg-primary)' }}>{s.latency.p50.toLocaleString()}</td>
                <td style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', fontFamily: 'var(--font-mono)', color: 'var(--fg-secondary)' }}>{s.latency.p95.toLocaleString()}</td>
                <td style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', fontFamily: 'var(--font-mono)', color: 'var(--fg-primary)', fontWeight: 500 }}>{(s.latency.p50 / 1000).toFixed(1)}s</td>
                <td style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', fontFamily: 'var(--font-mono)', color: 'var(--fg-secondary)' }}>{(s.latency.p95 / 1000).toFixed(1)}s</td>
                <td style={{ textAlign: 'right', padding: 'var(--space-2) var(--space-3)', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--fg-primary)' }}>{s.accuracy}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </GlassPanel>
  );
}