import React, { useEffect, useRef } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { getBarChartConfig, chartColors, chartColorsDark } from '../../utils/chartTheme';
import { useColorScheme } from '../../hooks/useReducedMotion';
import { GlassPanel } from '../ui/Card';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export function AccuracyChart({ data }) {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';
  const c = isDark ? chartColorsDark : chartColors;
  const chartRef = useRef(null);

  const chartData = {
    labels: data.systems.map(s => s.id),
    datasets: [
      {
        label: 'Accuracy (%)',
        data: data.systems.map(s => s.accuracy),
        backgroundColor: data.systems.map(s => s.isPrimary ? c.green : c.blue),
        borderColor: data.systems.map(s => s.isPrimary ? c.green : c.blue),
        borderWidth: 0,
        borderRadius: 6,
        borderSkipped: false,
        maxBarThickness: 48,
      },
    ],
  };

  const options = getBarChartConfig(isDark).options;

  // Add error bars for Wilson CI
  const plugin = {
    id: 'errorBars',
    afterDatasetsDraw(chart) {
      const ctx = chart.ctx;
      const meta = chart.getDatasetMeta(0);
      const dataset = chart.data.datasets[0];

      meta.data.forEach((bar, index) => {
        const ci = data.systems[index].wilsonCI;
        if (!ci) return;

        const xScale = chart.scales.x;
        const yScale = chart.scales.y;

        const barCenterX = bar.x;
        const barWidth = bar.width;

        // Calculate error bar positions (convert percentage to scale)
        const lower = yScale.getPixelForValue(ci[0]);
        const upper = yScale.getPixelForValue(ci[1]);
        const center = bar.y;

        ctx.save();
        ctx.strokeStyle = isDark ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.4)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 2]);

        // Vertical line
        ctx.beginPath();
        ctx.moveTo(barCenterX, lower);
        ctx.lineTo(barCenterX, upper);
        ctx.stroke();

        // Lower cap
        const capWidth = barWidth * 0.6;
        ctx.beginPath();
        ctx.moveTo(barCenterX - capWidth / 2, lower);
        ctx.lineTo(barCenterX + capWidth / 2, lower);
        ctx.stroke();

        // Upper cap
        ctx.beginPath();
        ctx.moveTo(barCenterX - capWidth / 2, upper);
        ctx.lineTo(barCenterX + capWidth / 2, upper);
        ctx.stroke();

        ctx.restore();
      });
    },
  };

  return (
    <GlassPanel padding="lg">
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <h3 style={{ margin: '0 0 var(--space-1)', fontSize: 'var(--text-lg)', fontWeight: 600 }}>
          5-Way System Accuracy Comparison
        </h3>
        <p style={{ margin: 0, fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)' }}>
          Wilson 95% confidence intervals shown as error bars. N=8 per system.
        </p>
      </div>
      <div style={{ height: '320px', position: 'relative' }}>
        <Bar
          ref={chartRef}
          data={chartData}
          options={{
            ...options,
            plugins: {
              ...options.plugins,
              legend: { display: false },
              tooltip: {
                ...options.plugins.tooltip,
                callbacks: {
                  label: (context) => {
                    const sys = data.systems[context.dataIndex];
                    return [
                      `Accuracy: ${context.parsed.y}% (${sys.correct}/${sys.total})`,
                      `Wilson 95% CI: [${sys.wilsonCI[0]}%, ${sys.wilsonCI[1]}%]`,
                      `Citation Resolution: ${sys.citationResolution}%`,
                      `Latency (p50/p95): ${(sys.latency.p50/1000).toFixed(1)}s / ${(sys.latency.p95/1000).toFixed(1)}s`,
                    ];
                  },
                },
              },
            },
          }}
          plugins={[plugin]}
        />
      </div>
      {/* Legend */}
      <div style={{ display: 'flex', gap: 'var(--space-6)', marginTop: 'var(--space-4)', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span style={{ width: '12px', height: '12px', borderRadius: '2px', background: c.blue }} />
          <span style={{ fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)' }}>Vector Baseline</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span style={{ width: '12px', height: '12px', borderRadius: '2px', background: c.green }} />
          <span style={{ fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)', fontWeight: 500 }}>Hybrid Auto-Routed (Primary)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span style={{ width: '12px', height: '12px', borderRadius: '2px', background: c.orange }} />
          <span style={{ fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)' }}>Other Systems</span>
        </div>
      </div>
    </GlassPanel>
  );
}