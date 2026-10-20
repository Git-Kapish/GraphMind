import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Database, Network, Cpu, BarChart3, Search } from 'lucide-react';
import { GlassPanel } from './ui/Card';
import { Button } from './ui/Button';

const springConfig = { type: 'spring', stiffness: 300, damping: 30, mass: 1 };

export default function TopBar({ health }) {
  const healthItems = [
    {
      key: 'postgres',
      icon: Database,
      label: 'PostgreSQL',
      value: '789 chunks',
      detail: 'pgvector 768-d nomic',
      status: health?.postgres || 'healthy',
    },
    {
      key: 'neo4j',
      icon: Network,
      label: 'Neo4j',
      value: '331 nodes',
      detail: '481 relationships',
      status: health?.neo4j || 'healthy',
    },
    {
      key: 'llm',
      icon: Cpu,
      label: 'LLM',
      value: 'Nemotron 3.5',
      detail: 'OpenRouter Free Tier',
      status: health?.llm || 'healthy',
    },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'var(--accent-green)';
      case 'degraded': return 'var(--accent-orange)';
      case 'unhealthy': return 'var(--accent-red)';
      default: return 'var(--accent-green)';
    }
  };

  return (
    <motion.header
      className="top-bar"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 'var(--topbar-height)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 var(--space-6)',
      }}
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springConfig}
    >
      <GlassPanel heavy padding="none" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', height: '100%', padding: '0 var(--space-4)' }}>
        {/* Brand */}
        <div className="top-bar-brand" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <Link to="/" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <span style={{
              fontFamily: 'var(--font-system)',
              fontSize: 'var(--text-xl)',
              fontWeight: 600,
              letterSpacing: 'var(--tracking-tight)',
              color: 'var(--fg-primary)',
            }}>
              GraphMind
            </span>
            <span style={{
              fontFamily: 'var(--font-system)',
              fontSize: 'var(--text-sm)',
              fontWeight: 500,
              color: 'var(--fg-tertiary)',
              textTransform: 'uppercase',
              letterSpacing: 'var(--tracking-wider)',
            }}>
              SEC 10-K RAG
            </span>
          </Link>
        </div>

        {/* Health Indicators */}
        <div className="top-bar-health" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }} aria-label="System health">
          {healthItems.map((item, index) => (
            <motion.div
              key={item.key}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                padding: 'var(--space-1) var(--space-3)',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--glass-border)',
                borderRadius: 'var(--radius-full)',
                fontSize: 'var(--text-sm)',
              }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...springConfig, delay: index * 0.05 }}
            >
              <item.icon size={14} style={{ color: getStatusColor(item.status) }} aria-hidden="true" />
              <span style={{ color: 'var(--fg-secondary)', whiteSpace: 'nowrap' }}>{item.label}</span>
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 'var(--text-xs)',
                color: 'var(--fg-primary)',
                fontVariantNumeric: 'tabular-nums',
              }}>
                {item.value}
              </span>
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: getStatusColor(item.status),
                  boxShadow: `0 0 8px ${getStatusColor(item.status)}`,
                }}
                aria-label={`${item.label} ${item.status}`}
              />
            </motion.div>
          ))}
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Button variant="ghost" size="sm" leftIcon={<Search size={14} />} className="hidden-sm">
            Search
          </Button>
          <Link to="/benchmark" style={{ textDecoration: 'none' }}>
            <Button variant="secondary" size="sm" leftIcon={<BarChart3 size={14} />}>
              Benchmark
            </Button>
          </Link>
        </div>
      </GlassPanel>
    </motion.header>
  );
}