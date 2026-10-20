/**
 * Chart.js Apple-inspired theme configuration
 * Matches the design system colors, typography, and spacing
 */

export const chartColors = {
  // Primary data colors (semantic)
  blue: '#0071E3',
  green: '#34C759',
  orange: '#FF9F0A',
  red: '#FF3B30',
  purple: '#AF52DE',
  pink: '#FF2D92',

  // System colors
  primary: '#1D1D1F',
  secondary: '#6E6E73',
  tertiary: '#86868B',
  quaternary: '#AEAEB2',

  // Backgrounds
  bgPrimary: '#FFFFFF',
  bgSecondary: '#F5F5F7',
  bgTertiary: '#EBEBF0',

  // Glass/border
  border: 'rgba(0, 0, 0, 0.06)',
  borderStrong: 'rgba(0, 0, 0, 0.1)',
};

export const chartColorsDark = {
  blue: '#0A84FF',
  green: '#30D158',
  orange: '#FF9F0A',
  red: '#FF453A',
  purple: '#BF5AF2',
  pink: '#FF375F',

  primary: '#F5F5F7',
  secondary: '#98989D',
  tertiary: '#8E8E93',
  quaternary: '#636366',

  bgPrimary: '#1D1D1F',
  bgSecondary: '#1D1D1F',
  bgTertiary: '#2C2C2E',

  border: 'rgba(255, 255, 255, 0.1)',
  borderStrong: 'rgba(255, 255, 255, 0.15)',
};

export function getChartTheme(isDark = false) {
  const c = isDark ? chartColorsDark : chartColors;

  return {
    color: c.primary,
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',

    // Global defaults
    defaults: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          align: 'start',
          labels: {
            usePointStyle: true,
            pointStyle: 'circle',
            padding: 20,
            font: {
              family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif',
              size: 13,
              weight: 500,
              lineHeight: 1.5,
            },
            color: c.secondary,
          },
        },
        tooltip: {
          enabled: true,
          backgroundColor: isDark ? 'rgba(28, 28, 30, 0.9)' : 'rgba(255, 255, 255, 0.9)',
          backdropFilter: 'blur(20px)',
          borderColor: c.border,
          borderWidth: 1,
          borderRadius: 12,
          padding: 16,
          titleFont: {
            family: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif',
            size: 14,
            weight: 600,
            lineHeight: 1.3,
          },
          bodyFont: {
            family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif',
            size: 13,
            weight: 400,
            lineHeight: 1.5,
          },
          footerFont: {
            family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif',
            size: 12,
            weight: 400,
            lineHeight: 1.5,
          },
          color: c.primary,
          titleColor: c.primary,
          bodyColor: c.secondary,
          footerColor: c.tertiary,
          displayColors: true,
          boxPadding: 8,
          usePointStyle: true,
          cornerRadius: 8,
          caretSize: 6,
          caretPadding: 12,
        },
      },
      scales: {
        x: {
          grid: {
            display: true,
            color: c.border,
            lineWidth: 1,
            drawBorder: false,
            drawOnChartArea: true,
            drawTicks: false,
          },
          ticks: {
            color: c.tertiary,
            font: {
              family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif',
              size: 12,
              weight: 400,
            },
            padding: 12,
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 10,
          },
          border: {
            display: false,
          },
        },
        y: {
          grid: {
            display: true,
            color: c.border,
            lineWidth: 1,
            drawBorder: false,
            drawOnChartArea: true,
            drawTicks: false,
          },
          ticks: {
            color: c.tertiary,
            font: {
              family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif',
              size: 12,
              weight: 400,
            },
            padding: 12,
            stepSize: 10,
          },
          border: {
            display: false,
          },
        },
      },
      animation: {
        duration: 600,
        easing: 'easeOutCubic',
      },
    },

    // Specific chart type overrides
    bar: {
      borderRadius: 6,
      borderSkipped: false,
      maxBarThickness: 48,
      minBarLength: 2,
    },

    line: {
      tension: 0.3,
      borderWidth: 2.5,
      pointRadius: 0,
      pointHoverRadius: 6,
      pointBackgroundColor: c.bgPrimary,
      pointBorderWidth: 2.5,
      fill: false,
    },

    doughnut: {
      cutout: '65%',
      borderWidth: 0,
      borderRadius: 4,
      spacing: 2,
    },

    scatter: {
      pointRadius: 6,
      pointHoverRadius: 8,
    },
  };
}

export function getBarChartConfig(isDark = false) {
  const theme = getChartTheme(isDark);
  const c = isDark ? chartColorsDark : chartColors;

  return {
    type: 'bar',
    data: { labels: [], datasets: [] },
    options: {
      ...theme.defaults,
      indexAxis: 'y',
      layout: {
        padding: { left: 16, right: 16, top: 8, bottom: 8 },
      },
      scales: {
        x: {
          ...theme.defaults.scales.x,
          beginAtZero: true,
          grid: {
            ...theme.defaults.scales.x.grid,
            drawOnChartArea: true,
          },
        },
        y: {
          ...theme.defaults.scales.y,
          grid: {
            ...theme.defaults.scales.y.grid,
            display: false,
          },
          ticks: {
            ...theme.defaults.scales.y.ticks,
            font: {
              ...theme.defaults.scales.y.ticks.font,
              size: 13,
            },
          },
        },
      },
      plugins: {
        ...theme.defaults.plugins,
        legend: {
          display: false,
        },
      },
    },
  };
}

export function getGroupedBarChartConfig(isDark = false) {
  const theme = getChartTheme(isDark);

  return {
    type: 'bar',
    data: { labels: [], datasets: [] },
    options: {
      ...theme.defaults,
      layout: {
        padding: { left: 16, right: 16, top: 8, bottom: 8 },
      },
      scales: {
        x: {
          ...theme.defaults.scales.x,
          grid: {
            ...theme.defaults.scales.x.grid,
            display: false,
          },
        },
        y: {
          ...theme.defaults.scales.y,
          beginAtZero: true,
          grid: {
            ...theme.defaults.scales.y.grid,
            drawOnChartArea: true,
          },
        },
      },
    },
  };
}

export function getStackedBarChartConfig(isDark = false) {
  const theme = getChartTheme(isDark);

  return {
    type: 'bar',
    data: { labels: [], datasets: [] },
    options: {
      ...theme.defaults,
      indexAxis: 'y',
      layout: {
        padding: { left: 16, right: 16, top: 8, bottom: 8 },
      },
      scales: {
        x: {
          ...theme.defaults.scales.x,
          stacked: true,
          beginAtZero: true,
        },
        y: {
          ...theme.defaults.scales.y,
          stacked: true,
          grid: {
            ...theme.defaults.scales.y.grid,
            display: false,
          },
        },
      },
      plugins: {
        ...theme.defaults.plugins,
        legend: {
          display: true,
          position: 'bottom',
          align: 'center',
        },
      },
    },
  };
}

export function getBoxPlotConfig(isDark = false) {
  const theme = getChartTheme(isDark);
  const c = isDark ? chartColorsDark : chartColors;

  // Box plot requires chartjs-chart-boxplot plugin
  return {
    type: 'boxplot',
    data: { labels: [], datasets: [] },
    options: {
      ...theme.defaults,
      indexAxis: 'y',
      layout: {
        padding: { left: 16, right: 16, top: 8, bottom: 8 },
      },
      scales: {
        x: {
          ...theme.defaults.scales.x,
          beginAtZero: true,
        },
        y: {
          ...theme.defaults.scales.y,
          grid: {
            ...theme.defaults.scales.y.grid,
            display: false,
          },
        },
      },
      plugins: {
        ...theme.defaults.plugins,
        legend: { display: false },
      },
      datasets: {
        boxplot: {
          backgroundColor: c.bgSecondary,
          borderColor: c.border,
          borderWidth: 1,
          itemRadius: 0,
          outlierRadius: 4,
          outlierColor: c.tertiary,
          median: {
            color: c.primary,
            width: 2,
          },
        },
      },
    },
  };
}