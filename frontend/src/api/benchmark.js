/**
 * Benchmark API Client
 * Fetches benchmark data from the backend
 */

const API_BASE = '/api';

export async function fetchBenchmarkResults() {
  try {
    const response = await fetch(`${API_BASE}/benchmark`);
    if (!response.ok) {
      throw new Error(`Failed to fetch benchmark: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Benchmark fetch error:', error);
    // Return fallback mock data for development
    return getMockBenchmarkData();
  }
}

export async function fetchBenchmarkSummary() {
  try {
    const response = await fetch(`${API_BASE}/benchmark/summary`);
    if (!response.ok) {
      throw new Error(`Failed to fetch benchmark summary: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Benchmark summary fetch error:', error);
    return getMockBenchmarkSummary();
  }
}

// Mock data for development/fallback
function getMockBenchmarkData() {
  return {
    meta: {
      targetModel: 'Qwen 2.5 3B',
      knowledgeGraph: '331 nodes / 481 edges',
      vectorStore: '789 chunks / 768-d nomic',
      citationResolution: '100.0%',
      timestamp: new Date().toISOString(),
    },
    systems: [
      {
        id: 'A',
        name: 'System A — Vector Baseline',
        accuracy: 87.5,
        correct: 7,
        total: 8,
        wilsonCI: [52.9, 97.8],
        citationResolution: 100.0,
        latency: { p50: 41935, p95: 55793 },
      },
      {
        id: 'B',
        name: 'System B — Graph-Only',
        accuracy: 50.0,
        correct: 4,
        total: 8,
        wilsonCI: [21.5, 78.5],
        citationResolution: 100.0,
        latency: { p50: 5103, p95: 11258 },
      },
      {
        id: 'C',
        name: 'System C — Hybrid Auto-Routed (Primary)',
        accuracy: 87.5,
        correct: 7,
        total: 8,
        wilsonCI: [52.9, 97.8],
        citationResolution: 100.0,
        latency: { p50: 28373, p95: 45482 },
        isPrimary: true,
      },
      {
        id: 'D',
        name: 'System D — Hybrid-Always',
        accuracy: 87.5,
        correct: 7,
        total: 8,
        wilsonCI: [52.9, 97.8],
        citationResolution: 100.0,
        latency: { p50: 3222, p95: 7147 },
      },
      {
        id: 'E',
        name: 'System E — Oracle Diagnostic',
        accuracy: 87.5,
        correct: 7,
        total: 8,
        wilsonCI: [52.9, 97.8],
        citationResolution: 100.0,
        latency: { p50: 2445, p95: 6520 },
      },
    ],
    categories: [
      {
        name: 'single_hop',
        sampleSize: 2,
        status: 'Exploratory (N < 15)',
        systems: {
          A: 100.0,
          B: 100.0,
          C: 100.0,
          D: 100.0,
          E: 100.0,
        },
        mcNemarPValue: 1.0,
      },
      {
        name: 'two_hop',
        sampleSize: 2,
        status: 'Exploratory (N < 15)',
        systems: {
          A: 100.0,
          B: 100.0,
          C: 100.0,
          D: 100.0,
          E: 100.0,
        },
        mcNemarPValue: 1.0,
      },
      {
        name: 'multi_hop',
        sampleSize: 2,
        status: 'Exploratory (N < 15)',
        systems: {
          A: 50.0,
          B: 50.0,
          C: 50.0,
          D: 50.0,
          E: 50.0,
        },
        mcNemarPValue: 1.0,
      },
      {
        name: 'out_of_scope',
        sampleSize: 2,
        status: 'Exploratory (N < 15)',
        systems: {
          A: 100.0,
          B: 100.0,
          C: 100.0,
          D: 100.0,
          E: 100.0,
        },
        mcNemarPValue: 1.0,
      },
    ],
    failureTaxonomy: [
      {
        system: 'A',
        name: 'System A (Vector Baseline)',
        retrievalMiss: 0,
        generationError: 1,
        refusalError: 0,
        routerError: 0,
        totalErrors: 1,
        notes: '',
      },
      {
        system: 'B',
        name: 'System B (Graph-Only)',
        retrievalMiss: 4,
        generationError: 0,
        refusalError: 0,
        routerError: 0,
        totalErrors: 4,
        notes: 'Refusal on unmodeled paths',
      },
      {
        system: 'C',
        name: 'System C (Hybrid Auto-Routed)',
        retrievalMiss: 0,
        generationError: 1,
        refusalError: 0,
        routerError: 0,
        totalErrors: 1,
        notes: 'Zero router errors',
        isPrimary: true,
      },
      {
        system: 'D',
        name: 'System D (Hybrid-Always)',
        retrievalMiss: 0,
        generationError: 1,
        refusalError: 0,
        routerError: 0,
        totalErrors: 1,
        notes: '',
      },
      {
        system: 'E',
        name: 'System E (Oracle Diagnostic)',
        retrievalMiss: 1,
        generationError: 0,
        refusalError: 0,
        routerError: 0,
        totalErrors: 1,
        notes: '',
      },
    ],
    takeaways: [
      {
        title: 'Hybrid Auto-Routing Works',
        description: 'System C matches Vector Baseline accuracy (87.5%) with zero router errors, while adding graph traversal for multi-hop queries.',
      },
      {
        title: 'Graph-Only Is Insufficient',
        description: 'System B fails on 50% of queries due to incomplete graph coverage — the KG contains only Exhibit 21 relationships.',
      },
      {
        title: 'Citation Resolution Is Robust',
        description: 'All 5 systems achieve 100% mechanical grounding — every answer cites verifiable SEC filing passages.',
      },
      {
        title: 'Latency Trade-off',
        description: 'Hybrid adds ~18s median latency vs Vector Baseline, but provides graph paths for auditability.',
      },
      {
        title: 'Sample Size Limitation',
        description: 'N=8 (2 per category) is exploratory only. Production deployment requires N ≥ 30 per category for statistical claims.',
      },
    ],
  };
}

function getMockBenchmarkSummary() {
  const data = getMockBenchmarkData();
  return {
    bestSystem: data.systems.find(s => s.isPrimary) || data.systems[2],
    overallAccuracy: data.systems[2].accuracy,
    totalSystems: data.systems.length,
    categoriesAnalyzed: data.categories.length,
  };
}