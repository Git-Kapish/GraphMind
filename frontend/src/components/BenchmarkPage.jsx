import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { ArrowLeft, BarChart3, Download, RefreshCw, Info, Cpu, Network, Database, ShieldCheck } from 'lucide-react';
import { GlassPanel } from './ui/Card';
import { Button } from './ui/Button';
import { AccuracyChart } from './Charts/AccuracyChart';
import { CategoryChart } from './Charts/CategoryChart';
import { FailureChart } from './Charts/FailureChart';
import { LatencyChart } from './Charts/LatencyChart';
import { fetchBenchmarkResults } from '../api/benchmark';
import { useIntersectionObserver } from '../hooks/useIntersectionObserver';

const springConfig = { type: 'spring', stiffness: 300, damping: 30, mass: 1 };
const staggerConfig = { delay: 0.1 };

// Individual observer hooks for each section (called at top level)
function useSectionObserver() {
  return useIntersectionObserver({
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px',
    triggerOnce: true,
  });
}

export default function BenchmarkPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refKey, setRefKey] = useState(0);

  // Create individual observers for each section
  const [accuracyRef, accuracyVisible] = useSectionObserver();
  const [categoryRef, categoryVisible] = useSectionObserver();
  const [failureRef, failureVisible] = useSectionObserver();
  const [latencyRef, latencyVisible] = useSectionObserver();
  const [takeawaysRef, takeawaysVisible] = useSectionObserver();
  const [metaRef, metaVisible] = useSectionObserver();

  const sectionRefs = {
    accuracy: accuracyRef,
    category: categoryRef,
    failure: failureRef,
    latency: latencyRef,
    takeaways: takeawaysRef,
    meta: metaRef,
  };

  const visibleSections = {
    accuracy: accuracyVisible,
    category: categoryVisible,
    failure: failureVisible,
    latency: latencyVisible,
    takeaways: takeawaysVisible,
    meta: metaVisible,
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchBenchmarkResults();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [refKey]);

  const handleRefresh = () => {
    setRefKey(k => k + 1);
  };

  if (loading) {
    return (
      <div className="benchmark-page" style={{ minHeight: '100vh', paddingTop: 'var(--topbar-height)' }}>
        <SkeletonLoader />
      </div>
    );
  }

  if (error) {
    return (
      <div className="benchmark-page" style={{ minHeight: '100vh', paddingTop: 'var(--topbar-height)', padding: 'var(--space-8)' }}>
        <GlassPanel padding="lg" style={{ maxWidth: '600px', margin: '0 auto', textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
            <div style={{ width: '48px', height: '48px', borderRadius: 'var(--radius-lg)', background: 'var(--accent-red-weak)', color: 'var(--accent-red)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Info size={24} />
            </div>
            <h2 style={{ margin: 0, fontSize: 'var(--text-xl)', fontWeight: 600 }}>Failed to Load Benchmark</h2>
          </div>
          <p style={{ margin: '0 0 var(--space-6)', color: 'var(--fg-secondary)' }}>
            {error}
          </p>
          <Button variant="primary" onClick={handleRefresh} leftIcon={<RefreshCw size={16} />}>
            Retry
          </Button>
        </GlassPanel>
      </div>
    );
  }

  return (
    <div className="benchmark-page" style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
      {/* Breadcrumb */}
      <nav className="benchmark-breadcrumb" aria-label="Breadcrumb" style={{ padding: 'var(--space-4) var(--space-6)', maxWidth: '1200px', margin: '0 auto' }}>
        <Link to="/" style={{
          display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)',
          color: 'var(--fg-secondary)', fontSize: 'var(--text-sm)', fontWeight: 500,
          transition: 'color 150ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        }}
        onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
        onMouseLeave={(e) => e.currentTarget.style.color = 'var(--fg-secondary)'}
        >
          <ArrowLeft size={16} aria-hidden="true" />
          <span>Back to Chat</span>
        </Link>
      </nav>

      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 var(--space-6) var(--space-12)' }}>
        {/* Page Header */}
        <motion.header
          ref={sectionRefs.meta}
          className="page-header"
          style={{ marginBottom: 'var(--space-8)' }}
          initial={{ opacity: 0, y: 20 }}
          animate={visibleSections.meta ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
                <div style={{ width: '40px', height: '40px', borderRadius: 'var(--radius-lg)', background: 'var(--accent-blue-weak)', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <BarChart3 size={20} />
                </div>
                <div>
                  <h1 style={{ margin: 0, fontSize: 'var(--text-3xl)', fontWeight: 600, letterSpacing: 'var(--tracking-tight)' }}>
                    Milestone M10: 5-Way Ablation Benchmark
                  </h1>
                  <p style={{ margin: 'var(--space-1) 0 0', fontSize: 'var(--text-base)', color: 'var(--fg-secondary)' }}>
                    Statistical Policy & Comprehensive Analysis
                  </p>
                </div>
              </div>
              <p style={{ margin: 0, fontSize: 'var(--text-lg)', color: 'var(--fg-secondary)', maxWidth: '700px' }}>
                Comprehensive benchmark analysis across 5 system configurations · Qwen 2.5 3B · 8 questions · 100% citation resolution
              </p>
            </div>

            {/* Meta Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-4)' }}>
              <MetaItem label="Target Model" value={data.meta.targetModel} icon={<Cpu size={16} />} />
              <MetaItem label="Knowledge Graph" value={data.meta.knowledgeGraph} color="var(--accent-green)" icon={<Network size={16} />} />
              <MetaItem label="Vector Store" value={data.meta.vectorStore} color="var(--accent-blue)" icon={<Database size={16} />} />
              <MetaItem label="Citation Resolution" value={data.meta.citationResolution} color="var(--accent-green)" icon={<ShieldCheck size={16} />} isHighlight={true} />
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
              <Button variant="secondary" leftIcon={<RefreshCw size={16} />} onClick={handleRefresh}>
                Refresh Data
              </Button>
              <Button variant="ghost" leftIcon={<Download size={16} />} onClick={() => window.print()}>
                Export PDF
              </Button>
            </div>
          </div>
        </motion.header>

        {/* Section 1: Accuracy Comparison */}
        <motion.section
          ref={sectionRefs.accuracy}
          className="benchmark-section"
          initial={{ opacity: 0, y: 30 }}
          animate={visibleSections.accuracy ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94], delay: 0.1 }}
        >
          <AccuracyChart data={data} />
        </motion.section>

        {/* Section 2: Category Breakdown */}
        <motion.section
          ref={sectionRefs.category}
          className="benchmark-section"
          initial={{ opacity: 0, y: 30 }}
          animate={visibleSections.category ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94], delay: 0.2 }}
        >
          <CategoryChart data={data} />
        </motion.section>

        {/* Section 3: Failure Taxonomy */}
        <motion.section
          ref={sectionRefs.failure}
          className="benchmark-section"
          initial={{ opacity: 0, y: 30 }}
          animate={visibleSections.failure ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94], delay: 0.3 }}
        >
          <FailureChart data={data} />
        </motion.section>

        {/* Section 4: Latency */}
        <motion.section
          ref={sectionRefs.latency}
          className="benchmark-section"
          initial={{ opacity: 0, y: 30 }}
          animate={visibleSections.latency ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94], delay: 0.4 }}
        >
          <LatencyChart data={data} />
        </motion.section>

        {/* Section 5: Key Takeaways */}
        <motion.section
          ref={sectionRefs.takeaways}
          className="benchmark-section"
          initial={{ opacity: 0, y: 30 }}
          animate={visibleSections.takeaways ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
          transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94], delay: 0.5 }}
        >
          <GlassPanel padding="lg">
            <h2 style={{ margin: '0 0 var(--space-6)', fontSize: 'var(--text-xl)', fontWeight: 600 }}>
              Key Takeaways
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-4)' }}>
              {data.takeaways.map((takeaway, idx) => (
                <motion.div
                  key={idx}
                  style={{
                    padding: 'var(--space-5)',
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--glass-border)',
                    borderRadius: 'var(--radius-lg)',
                    display: 'flex',
                    gap: 'var(--space-3)',
                  }}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.6 + idx * 0.1, ease: [0.25, 0.46, 0.45, 0.94] }}
                >
                  <div style={{
                    width: '40px', height: '40px', borderRadius: 'var(--radius-md)',
                    background: 'var(--accent-blue-weak)', color: 'var(--accent-blue)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>
                    <Info size={20} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <h4 style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--fg-primary)' }}>
                      {takeaway.title}
                    </h4>
                    <p style={{ margin: 0, fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
                      {takeaway.description}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </GlassPanel>
        </motion.section>

        {/* Footer */}
        <motion.footer
          style={{ marginTop: 'var(--space-12)', paddingTop: 'var(--space-8)', borderTop: '1px solid var(--glass-border)', textAlign: 'center' }}
          initial={{ opacity: 0 }}
          animate={visibleSections.meta ? { opacity: 1 } : { opacity: 0 }}
          transition={{ delay: 0.8 }}
        >
          <p style={{ margin: 0, fontSize: 'var(--text-sm)', color: 'var(--fg-tertiary)' }}>
            GraphMind Benchmark · Data from Milestone M10 evaluation ·{' '}
            <span style={{ fontFamily: 'var(--font-mono)' }}>{new Date(data.meta.timestamp).toLocaleDateString()}</span>
          </p>
        </motion.footer>
      </main>
    </div>
  );
}

// Helper Components
function MetaItem({ label, value, color = 'var(--fg-primary)', icon: Icon, isHighlight = false }) {
  return (
    <div style={{
      padding: 'var(--space-4)',
      background: 'var(--bg-secondary)',
      border: '1px solid var(--glass-border)',
      borderRadius: 'var(--radius-lg)',
      display: 'flex', flexDirection: 'column', gap: 'var(--space-2)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
        {Icon && <Icon style={{ color: 'var(--fg-tertiary)' }} />}
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--fg-tertiary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)', fontWeight: 500 }}>
          {label}
        </span>
      </div>
      <span style={{
        fontSize: isHighlight ? 'var(--text-lg)' : 'var(--text-base)',
        fontWeight: isHighlight ? 600 : 500,
        fontFamily: 'var(--font-mono)',
        color,
        fontVariantNumeric: 'tabular-nums',
      }}>
        {value}
      </span>
    </div>
  );
}

function SkeletonLoader() {
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: 'var(--space-6)' }}>
      <div style={{ height: '60px', background: 'linear-gradient(90deg, var(--bg-tertiary) 25%, var(--bg-quaternary) 50%, var(--bg-tertiary) 75%)', backgroundSize: '200% 100%', animation: 'shimmer 1.5s infinite', borderRadius: 'var(--radius-lg)', marginBottom: 'var(--space-8)' }} />
      {[1, 2, 3, 4, 5].map(i => (
        <div key={i} style={{ height: '350px', background: 'linear-gradient(90deg, var(--bg-tertiary) 25%, var(--bg-quaternary) 50%, var(--bg-tertiary) 75%)', backgroundSize: '200% 100%', animation: 'shimmer 1.5s infinite', borderRadius: 'var(--radius-lg)', marginBottom: 'var(--space-6)' }} />
      ))}
      <style jsx>{`
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  );
}

// Icons imported at top