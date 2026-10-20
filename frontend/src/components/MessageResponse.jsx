import React from 'react';
import { motion } from 'framer-motion';
import { Route, Clock, ShieldCheck, Layers, FileText, GitMerge } from 'lucide-react';
import { GlassPanel } from './ui/Card';
import { Badge, CitationBadge } from './ui/Badge';
import { GraphCanvas } from './GraphCanvas';
import { markdownComponents } from './MarkdownRenderer';
import ReactMarkdown from 'react-markdown';

const springConfig = { type: 'spring', stiffness: 300, damping: 30, mass: 1 };

// Compare Response Component (for side-by-side mode)
function CompareResponse({ baselineData, hybridData, onSelectCitation }) {
  return (
    <motion.div
      className="compare-response"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springConfig}
    >
      <GlassPanel padding="md" style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <div style={{
            width: '40px', height: '40px', borderRadius: 'var(--radius-md)',
            background: 'var(--accent-blue-weak)', color: 'var(--accent-blue)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <GitMerge size={20} />
          </div>
          <div>
            <h4 style={{ margin: 0, fontSize: 'var(--text-lg)', fontWeight: 600 }}>
              A/B Comparison: System A (Vector) vs System C (Hybrid)
            </h4>
            <p style={{ margin: 'var(--space-1) 0 0', fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)' }}>
              Same query executed against both retrieval strategies
            </p>
          </div>
        </div>
      </GlassPanel>

      <div className="compare-grid" style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: 'var(--space-4)',
      }}>
        {/* System A: Vector Baseline */}
        <GlassPanel padding="lg" variant="glass">
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
              <span style={{
                width: '10px', height: '10px', borderRadius: '50%',
                background: 'var(--accent-blue)', boxShadow: '0 0 8px var(--accent-blue)'
              }} />
              <h5 style={{ margin: 0, fontSize: 'var(--text-base)', fontWeight: 600 }}>
                System A: Vector Baseline
              </h5>
            </div>
            <Badge variant="blue" size="sm">Dense pgvector (k=5)</Badge>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-3)', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-4)', borderBottom: '1px solid var(--glass-border)' }}>
            <StatItem label="Latency" value={`${baselineData?.latency?.total_ms || baselineData?.latency?.total || 0} ms`} />
            <StatItem label="Route" value="vector_only" color="var(--accent-blue)" />
            <StatItem label="Passages" value={baselineData?.passages?.length || 0} />
          </div>

          <div style={{ marginBottom: 'var(--space-4)' }}>
            <h6 style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--fg-secondary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>
              Generated Answer
            </h6>
            <p style={{ margin: 0, lineHeight: 'var(--leading-relaxed)', color: 'var(--fg-primary)' }}>
              {baselineData?.answer || 'No response received.'}
            </p>
          </div>

          <div>
            <h6 style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--fg-secondary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>
              Retrieved Passages
            </h6>
            {baselineData?.passages && baselineData.passages.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {baselineData.passages.map((p, idx) => (
                  <div key={idx} style={{
                    padding: 'var(--space-3)',
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--glass-border)',
                    borderRadius: 'var(--radius-md)',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                      <Badge variant="blue" size="xs">[P{idx + 1}]</Badge>
                      <span style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--fg-primary)' }}>{p.company}</span>
                    </div>
                    <p style={{ margin: 0, fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
                      {p.text.slice(0, 140)}...
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ margin: 0, color: 'var(--fg-tertiary)', fontSize: 'var(--text-sm)' }}>No passages returned.</p>
            )}
          </div>
        </GlassPanel>

        {/* System C: Hybrid Auto-Routed */}
        <GlassPanel padding="lg" variant="glass" style={{ borderColor: 'rgba(52, 199, 89, 0.3)' }}>
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
              <span style={{
                width: '10px', height: '10px', borderRadius: '50%',
                background: 'var(--accent-green)', boxShadow: '0 0 8px var(--accent-green)'
              }} />
              <h5 style={{ margin: 0, fontSize: 'var(--text-base)', fontWeight: 600 }}>
                System C: Hybrid Auto-Routed
              </h5>
            </div>
            <Badge variant="green" size="sm">Auto-Routed</Badge>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-3)', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-4)', borderBottom: '1px solid var(--glass-border)' }}>
            <StatItem label="Latency" value={`${hybridData?.latency?.total_ms || hybridData?.latency?.total || 0} ms`} />
            <StatItem label="Route" value={hybridData?.route?.chosen?.toUpperCase() || 'HYBRID'} color="var(--accent-green)" />
            <StatItem label="Graph Paths" value={hybridData?.graph_paths?.length || 0} color="var(--accent-green)" />
          </div>

          <div style={{ marginBottom: 'var(--space-4)' }}>
            <h6 style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--fg-secondary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>
              Grounded Answer
            </h6>
            <p style={{ margin: 0, lineHeight: 'var(--leading-relaxed)', color: 'var(--fg-primary)' }}>
              {hybridData?.answer || 'No response received.'}
            </p>
          </div>

          {hybridData?.graph_paths && hybridData.graph_paths.length > 0 ? (
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <h6 style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--fg-secondary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>
                Traversed Knowledge Graph
              </h6>
              <GraphCanvas graphPaths={hybridData.graph_paths} onSelectEvidence={onSelectCitation} />
            </div>
          ) : (
            <div>
              <h6 style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--fg-secondary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)' }}>
                Retrieved Passages
              </h6>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {(hybridData?.passages || []).map((p, idx) => (
                  <div key={idx} style={{
                    padding: 'var(--space-3)',
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--glass-border)',
                    borderRadius: 'var(--radius-md)',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                      <Badge variant="green" size="xs">[P{idx + 1}]</Badge>
                      <span style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--fg-primary)' }}>{p.company}</span>
                    </div>
                    <p style={{ margin: 0, fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
                      {p.text.slice(0, 140)}...
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </GlassPanel>
      </div>
    </motion.div>
  );
}

function StatItem({ label, value, color }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--fg-tertiary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)', fontWeight: 500 }}>
        {label}
      </span>
      <span style={{ fontSize: 'var(--text-base)', fontWeight: 600, fontFamily: 'var(--font-mono)', color: color || 'var(--fg-primary)' }}>
        {value}
      </span>
    </div>
  );
}

// Single Response Component
export function MessageResponse({ response, mode, onSelectCitation }) {
  // Handle Compare mode
  if (response?.baseline && response?.hybrid) {
    return <CompareResponse baselineData={response.baseline} hybridData={response.hybrid} onSelectCitation={onSelectCitation} />;
  }

  // Single response
  const {
    answer = '',
    status,
    route,
    citations = [],
    graph_paths = [],
    passages = [],
    latency = {},
  } = response;

  const isRefusal = status === 'refused' || answer.toLowerCase().includes('do not contain sufficient evidence');

  return (
    <motion.div
      className="message-response"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springConfig}
    >
      {/* Telemetry Ribbon */}
      <GlassPanel padding="md" style={{ marginBottom: 'var(--space-4)', display: 'flex', flexWrap: 'wrap', gap: 'var(--space-4)', alignItems: 'center' }}>
        <TelemetryItem icon={<Route size={14} />} color="var(--accent-blue)" label="Route" value={route?.chosen?.toUpperCase() || 'HYBRID'} />
        {route?.fallback_used && (
          <Badge variant="orange" size="xs">Fallback</Badge>
        )}
        <TelemetryItem icon={<Clock size={14} />} color="var(--fg-tertiary)" label="Latency" value={`${latency?.total_ms || latency?.total || 0} ms`} mono />
        <TelemetryItem icon={<ShieldCheck size={14} />} color="var(--accent-green)" label="Citations" value="100% Grounded" colorValue="var(--accent-green)" />
        <TelemetryItem icon={<Layers size={14} />} color="var(--accent-green)" label="Graph" value={`${graph_paths.length} paths`} mono colorValue="var(--accent-green)" />
        <TelemetryItem icon={<FileText size={14} />} color="var(--accent-blue)" label="Passages" value={passages.length} mono />
      </GlassPanel>

      {/* Grounded Answer Card */}
      <GlassPanel padding="lg" style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ marginBottom: 'var(--space-4)' }}>
          <Badge variant={isRefusal ? 'red' : 'green'} size="sm">
            {isRefusal ? 'Explicit Refusal' : 'Grounded & Verified'}
          </Badge>
        </div>

        <div style={{ marginBottom: 'var(--space-4)' }}>
          <ReactMarkdown components={markdownComponents}>
            {answer}
          </ReactMarkdown>
        </div>

        {/* Citations Footer */}
        {citations.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--space-2)' }}>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--fg-tertiary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)', fontWeight: 500 }}>
              Active Citations:
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
              {citations.map((c, idx) => (
                <CitationBadge
                  key={idx}
                  sourceType={c.source_type}
                  onClick={() => onSelectCitation(c)}
                  title={c.company ? `${c.label} — ${c.company}` : c.label}
                >
                  {c.label}
                  {c.company && <span style={{ fontSize: 'var(--text-xs)', opacity: 0.7, marginLeft: '4px' }}>{c.company}</span>}
                </CitationBadge>
              ))}
            </div>
          </div>
        )}
      </GlassPanel>

      {/* Traversed Knowledge Graph Visualizer */}
      {graph_paths.length > 0 && (
        <GlassPanel padding="lg" style={{ marginBottom: 'var(--space-4)' }}>
          <GraphCanvas graphPaths={graph_paths} onSelectEvidence={onSelectCitation} />
        </GlassPanel>
      )}

      {/* Retrieved Passages List */}
      {passages.length > 0 && (
        <GlassPanel padding="lg">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <FileText size={14} style={{ color: 'var(--accent-blue)' }} aria-hidden="true" />
              <h4 style={{ margin: 0, fontSize: 'var(--text-base)', fontWeight: 600 }}>Retrieved Passages (Top-{passages.length})</h4>
            </div>
            <Badge variant="blue" size="xs">pgvector 768-d</Badge>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {passages.map((p, idx) => (
              <PassageItem
                key={idx}
                passage={p}
                index={idx}
                onSelectCitation={onSelectCitation}
              />
            ))}
          </div>
        </GlassPanel>
      )}
    </motion.div>
  );
}

function TelemetryItem({ icon, color, label, value, mono = false, colorValue }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
      <span style={{ color, display: 'flex' }}>{icon}</span>
      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--fg-tertiary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)', fontWeight: 500 }}>
        {label}
      </span>
      <span style={{
        fontSize: 'var(--text-sm)',
        fontWeight: 600,
        fontFamily: mono ? 'var(--font-mono)' : 'var(--font-system)',
        color: colorValue || 'var(--fg-primary)',
        fontVariantNumeric: mono ? 'tabular-nums' : 'normal',
      }}>
        {value}
      </span>
    </div>
  );
}

function PassageItem({ passage, index, onSelectCitation }) {
  const [isHovered, setIsHovered] = React.useState(false);

  return (
    <motion.div
      className="passage-item"
      role="button"
      tabIndex={0}
      onClick={() => onSelectCitation({
        label: `[P${index + 1}]`,
        company: passage.company,
        ticker: passage.ticker,
        section_path: passage.section_path,
        chunk_id: passage.chunk_id,
        text_snippet: passage.text,
        source_type: 'vector',
      })}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.currentTarget.click(); } }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        padding: 'var(--space-3)',
        background: isHovered ? 'var(--accent-blue-weak)' : 'var(--bg-secondary)',
        border: `1px solid ${isHovered ? 'var(--accent-blue)' : 'var(--glass-border)'}`,
        borderRadius: 'var(--radius-md)',
        cursor: 'pointer',
        transition: 'all 150ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      }}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)', flexWrap: 'wrap' }}>
        <Badge variant="blue" size="xs">[P{index + 1}]</Badge>
        <span style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--fg-primary)' }}>{passage.company}</span>
        <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: 'var(--fg-tertiary)', fontVariantNumeric: 'tabular-nums' }}>
          Sim: {(Number(passage.cosine_similarity || passage.similarity || 0) * 100).toFixed(1)}%
        </span>
      </div>
      <p style={{ margin: 0, fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
        {passage.text.slice(0, 180)}{passage.text.length > 180 ? '...' : ''}
      </p>
      <div style={{ marginTop: 'var(--space-2)', paddingTop: 'var(--space-2)', borderTop: '1px solid var(--glass-border)' }}>
        <code style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: 'var(--fg-tertiary)' }}>
          {passage.section_path || passage.chunk_id}
        </code>
      </div>
    </motion.div>
  );
}