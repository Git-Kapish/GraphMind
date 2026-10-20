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

export function CategoryChart({ data }) {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';
  const c = isDark ? chartColorsDark : chartColors;

  const systems = ['A', 'B', 'C', 'D', 'E'];
  const systemColors = {
    A: c.blue,
    B: c.orange,
    C: c.green,
    D: c.purple,
    E: c.pink,
  };

  const chartData = {
    labels: data.categories.map(c => c.name.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())),
    datasets: systems.map(sysId => ({
      label: `System ${sysId}`,
      data: data.categories.map(cat => cat.systems[sysId] || 0),
      backgroundColor: systemColors[sysId],
      borderColor: systemColors[sysId],
      borderWidth: 0,
      borderRadius: 4,
      borderSkipped: false,
    })),
  };

  const options = getGroupedBarChartConfig(isDark).options;

  return (
    <GlassPanel padding="lg">
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <h3 style={{ margin: '0 0 var(--space-1)', fontSize: 'var(--text-lg)', fontWeight: 600 }}>
          Category Breakdown by System
        </h3>
        <p style={{ margin: 0, fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)' }}>
          Accuracy per category. All categories exploratory (N=2). Statistical status per PRD §2.2.
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
                position: 'bottom',
                align: 'center',
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
                    const cat = data.categories[context.dataIndex];
                    const sysId = context.dataset.label.replace('System ', '');
                    return [
                      `${context.dataset.label}: ${context.parsed.y}%`,
                      `Status: ${cat.status}`,
                      `McNemar p-value: ${cat.mcNemarPValue.toFixed(4)}`,
                    ];
                  },
                },
              },
            },
          }}
        />
      </div>
    </GlassPanel>
  );
}