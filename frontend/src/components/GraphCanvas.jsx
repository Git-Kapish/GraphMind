import React, { useState, useEffect, useRef, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Network, Info, Maximize2, ZoomIn, ZoomOut, RotateCcw, X } from 'lucide-react';
import { Badge } from './ui/Badge';
import * as d3 from 'd3-force';
import { GlassPanel } from './ui/Card';
import { IconButton } from './ui/Button';

const springConfig = { type: 'spring', stiffness: 300, damping: 30, mass: 1 };

export function GraphCanvas({ graphPaths, onSelectEvidence }) {
  const [selectedItem, setSelectedItem] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const svgRef = useRef(null);
  const containerRef = useRef(null);

  // Flatten nodes and edges from all graph paths
  const { allNodes, allEdges } = useMemo(() => {
    if (!graphPaths || graphPaths.length === 0) {
      return { allNodes: [], allEdges: [] };
    }
    const nodes = [];
    const edges = [];
    const nodeSet = new Set();

    graphPaths.forEach((path, pathIdx) => {
      const pathNodes = path.nodes || [];
      const relations = path.relations || [];
      const evidence = path.evidence || [];

      pathNodes.forEach((nodeName) => {
        if (!nodeSet.has(nodeName)) {
          nodeSet.add(nodeName);
          // Categorize type heuristically
          let type = 'Entity';
          const lower = nodeName.toLowerCase();
          if (lower.includes('corp') || lower.includes('inc') || lower.includes('technolog') || lower.includes('micro') || lower.includes('devices')) {
            type = 'Company';
          } else if (lower.includes('singapore') || lower.includes('ireland') || lower.includes('delaware') || lower.includes('california') || lower.includes('israel') || lower.includes('finland')) {
            type = 'Location';
          } else if (lower.includes('pte') || lower.includes('ltd') || lower.includes('gmbh') || lower.includes('oy') || lower.includes('services')) {
            type = 'Subsidiary';
          }

          nodes.push({
            id: nodeName,
            label: nodeName,
            type,
            pathIndex: pathIdx,
          });
        }
      });

      for (let i = 0; i < relations.length; i++) {
        const source = pathNodes[i];
        const target = pathNodes[i + 1];
        const rel = relations[i];
        const ev = evidence[i] || evidence[0];

        if (source && target) {
          edges.push({
            id: `edge_${pathIdx}_${i}`,
            source,
            target,
            relation: rel,
            evidence: ev,
          });
        }
      }
    });

    return { allNodes: nodes, allEdges: edges };
  }, [graphPaths]);

  // Use d3-force for layout
  const [nodePositions, setNodePositions] = useState({});

  useEffect(() => {
    if (allNodes.length === 0) return;

    const width = containerRef.current?.clientWidth || 640;
    const height = Math.max(300, allNodes.length * 60);

    // Create simulation
    const simulation = d3.forceSimulation(allNodes)
      .force('link', d3.forceLink(allEdges).id(d => d.id).distance(120).strength(0.7))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(40).strength(0.8))
      .force('x', d3.forceX(width / 2).strength(0.1))
      .force('y', d3.forceY(height / 2).strength(0.1))
      .alphaDecay(0.02)
      .velocityDecay(0.4);

    simulation.on('tick', () => {
      const positions = {};
      allNodes.forEach(node => {
        positions[node.id] = { x: node.x, y: node.y };
      });
      setNodePositions(positions);
    });

    // Run for a few ticks then stop
    const iterations = 150;
    for (let i = 0; i < iterations; i++) {
      simulation.tick();
    }
    simulation.stop();
  }, [allNodes, allEdges]);

  const getNodeColor = (type) => {
    switch (type) {
      case 'Company':
        return { fill: '#1E1B4B', stroke: '#6366F1', text: '#C7D2FE', glow: 'rgba(99, 102, 241, 0.4)', icon: 'building' };
      case 'Subsidiary':
        return { fill: '#022C22', stroke: '#34C759', text: '#6EE7B7', glow: 'rgba(52, 199, 89, 0.4)', icon: 'building-2' };
      case 'Location':
        return { fill: '#451A03', stroke: '#FF9F0A', text: '#FDE68A', glow: 'rgba(255, 159, 10, 0.4)', icon: 'map-pin' };
      default:
        return { fill: '#1E293B', stroke: '#64748B', text: '#94A3B8', glow: 'rgba(148, 163, 184, 0.3)', icon: 'circle' };
    }
  };

  const handleZoom = (event) => {
    event.preventDefault();
    const delta = event.deltaY > 0 ? 0.9 : 1.1;
    const newK = Math.min(Math.max(transform.k * delta, 0.3), 3);
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect) {
      const mouseX = event.clientX - rect.left;
      const mouseY = event.clientY - rect.top;
      const newX = mouseX - (mouseX - transform.x) * (newK / transform.k);
      const newY = mouseY - (mouseY - transform.y) * (newK / transform.k);
      setTransform({ x: newX, y: newY, k: newK });
    }
  };

  const handlePanStart = (event) => {
    const startX = event.clientX - transform.x;
    const startY = event.clientY - transform.y;

    const handlePanMove = (e) => {
      setTransform({
        x: e.clientX - startX,
        y: e.clientY - startY,
        k: transform.k,
      });
    };

    const handlePanEnd = () => {
      window.removeEventListener('mousemove', handlePanMove);
      window.removeEventListener('mouseup', handlePanEnd);
    };

    window.addEventListener('mousemove', handlePanMove);
    window.addEventListener('mouseup', handlePanEnd);
  };

  const resetView = () => {
    setTransform({ x: 0, y: 0, k: 1 });
  };

  const zoomIn = () => {
    setTransform(t => ({ ...t, k: Math.min(t.k * 1.3, 3) }));
  };

  const zoomOut = () => {
    setTransform(t => ({ ...t, k: Math.max(t.k / 1.3, 0.3) }));
  };

  const width = isExpanded ? 900 : 640;
  const height = Math.max(300, allNodes.length * 60);

  return (
    <div className="graph-canvas-wrapper" style={{ borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
      <div className="graph-canvas-header" style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: 'var(--space-4)', borderBottom: '1px solid var(--glass-border)',
        background: 'var(--bg-secondary)'
      }}>
        <div className="graph-title-strip" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Network size={16} style={{ color: 'var(--accent-green)' }} aria-hidden="true" />
          <span className="graph-canvas-title" style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--fg-primary)' }}>
            Traversed Knowledge Graph Path ({allNodes.length} Nodes, {allEdges.length} Relations)
          </span>
        </div>
        <div className="graph-canvas-actions" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Badge variant="green" size="xs">Verified Neo4j Traversal</Badge>
          <IconButton variant="subtle" size="sm" onClick={zoomIn} aria-label="Zoom in" title="Zoom in">
            <ZoomIn size={16} />
          </IconButton>
          <IconButton variant="subtle" size="sm" onClick={zoomOut} aria-label="Zoom out" title="Zoom out">
            <ZoomOut size={16} />
          </IconButton>
          <IconButton variant="subtle" size="sm" onClick={resetView} aria-label="Reset view" title="Reset view">
            <RotateCcw size={16} />
          </IconButton>
          <IconButton
            variant="subtle"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-label={isExpanded ? 'Collapse graph' : 'Expand graph'}
            title={isExpanded ? 'Collapse' : 'Expand'}
          >
            <Maximize2 size={16} />
          </IconButton>
        </div>
      </div>

      <div
        ref={containerRef}
        className="svg-container"
        style={{
          height: isExpanded ? '500px' : 'auto',
          minHeight: '300px',
          position: 'relative',
          background: 'var(--bg-primary)',
        }}
        onWheel={handleZoom}
        onMouseDown={handlePanStart}
      >
        <svg
          ref={svgRef}
          width="100%"
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          className="graph-svg"
          role="img"
          aria-label="Knowledge graph traversal visualization"
          style={{
            transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.k})`,
            transformOrigin: '0 0',
            transition: 'transform 100ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
          }}
        >
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="24"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#34C759" />
            </marker>
            <filter id="node-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background grid */}
          <g style={{ opacity: 0.03 }}>
            {[...Array(20)].map((_, i) => (
              <line key={i} x1={i * 50} y1={0} x2={i * 50} y2={height} stroke="currentColor" strokeWidth="0.5" />
            ))}
            {[...Array(12)].map((_, i) => (
              <line key={i} x1={0} y1={i * 50} x2={width} y2={i * 50} stroke="currentColor" strokeWidth="0.5" />
            ))}
          </g>

          {/* Render Relationship Edges */}
          {allEdges.map((edge) => {
            const src = nodePositions[edge.source];
            const dst = nodePositions[edge.target];
            if (!src || !dst) return null;

            const midX = (src.x + dst.x) / 2;
            const midY = (src.y + dst.y) / 2;

            return (
              <motion.g
                key={edge.id}
                className="graph-edge-group"
                onClick={() => setSelectedItem({ type: 'edge', data: edge })}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedItem({ type: 'edge', data: edge }); } }}
                tabIndex={0}
                role="button"
                aria-label={`Relationship: ${edge.source} ${edge.relation} ${edge.target}`}
                whileHover={{ strokeWidth: 3 }}
                whileTap={{ scale: 1.02 }}
                style={{ cursor: 'pointer' }}
              >
                <line
                  x1={src.x}
                  y1={src.y}
                  x2={dst.x}
                  y2={dst.y}
                  stroke="#34C759"
                  strokeWidth="2"
                  strokeDasharray="6,4"
                  markerEnd="url(#arrowhead)"
                  className="edge-line"
                  style={{ filter: 'drop-shadow(0 0 3px rgba(52, 199, 89, 0.3))' }}
                />
                <motion.rect
                  x={midX - 50}
                  y={midY - 12}
                  width="100"
                  height="20"
                  rx="4"
                  fill="#081428"
                  stroke="rgba(52, 199, 89, 0.3)"
                  strokeWidth="1"
                  whileHover={{ fill: '#0A1A30', stroke: 'rgba(52, 199, 89, 0.5)' }}
                />
                <text
                  x={midX}
                  y={midY + 3}
                  textAnchor="middle"
                  fill="#6EE7B7"
                  fontSize="9"
                  fontFamily="var(--font-mono)"
                  fontWeight="600"
                  pointerEvents="none"
                >
                  {edge.relation}
                </text>
              </motion.g>
            );
          })}

          {/* Render Entity Nodes */}
          {allNodes.map((node) => {
            const coord = nodePositions[node.id];
            if (!coord) return null;
            const colors = getNodeColor(node.type);

            return (
              <motion.g
                key={node.id}
                className="graph-node-group"
                transform={`translate(${coord.x}, ${coord.y})`}
                onClick={() => setSelectedItem({ type: 'node', data: node })}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedItem({ type: 'node', data: node }); } }}
                tabIndex={0}
                role="button"
                aria-label={`${node.label}, ${node.type}`}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                style={{ cursor: 'pointer' }}
              >
                <motion.circle
                  r="22"
                  fill={colors.fill}
                  stroke={colors.stroke}
                  strokeWidth="2"
                  className="node-circle"
                  filter="url(#node-glow)"
                  animate={{ r: [22, 23, 22] }}
                  transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                />
                <text
                  y="32"
                  textAnchor="middle"
                  fill={colors.text}
                  fontSize="11"
                  fontWeight="600"
                  fontFamily="var(--font-system)"
                  className="node-label"
                  pointerEvents="none"
                >
                  {node.label.length > 24 ? node.label.slice(0, 22) + '...' : node.label}
                </text>
                <text
                  y="44"
                  textAnchor="middle"
                  fill={colors.stroke}
                  fontSize="8"
                  fontFamily="var(--font-mono)"
                  className="node-type"
                  pointerEvents="none"
                >
                  {node.type}
                </text>
              </motion.g>
            );
          })}
        </svg>
      </div>

      {/* Selected Node/Edge Detail Strip */}
      {selectedItem && (
        <motion.div
          className="graph-detail-box"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={springConfig}
          style={{
            padding: 'var(--space-4)',
            borderTop: '1px solid var(--glass-border)',
            background: 'var(--bg-secondary)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Info size={14} style={{ color: 'var(--accent-blue)' }} aria-hidden="true" />
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--fg-primary)' }}>
                {selectedItem.type === 'node'
                  ? `Entity: ${selectedItem.data.label} (${selectedItem.data.type})`
                  : `Relationship: ${selectedItem.data.relation}`}
              </span>
            </div>
            <button
              onClick={() => setSelectedItem(null)}
              aria-label="Close details"
              style={{
                width: '28px', height: '28px', borderRadius: 'var(--radius-sm)',
                background: 'transparent', border: 'none', color: 'var(--fg-tertiary)',
                cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-tertiary)'; e.currentTarget.style.color = 'var(--fg-primary)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--fg-tertiary)'; }}
            >
              <X size={16} />
            </button>
          </div>
          {selectedItem.type === 'edge' && selectedItem.data.evidence && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <p style={{ margin: 0, padding: 'var(--space-3)', background: 'var(--accent-green-weak)', border: '1px solid rgba(52, 199, 89, 0.2)', borderRadius: 'var(--radius-md)', fontStyle: 'italic', color: 'var(--fg-primary)', lineHeight: 'var(--leading-relaxed)', fontSize: 'var(--text-sm)' }}>
                "{selectedItem.data.evidence.evidence_quote}"
              </p>
              <div style={{ display: 'flex', gap: 'var(--space-4)', fontSize: 'var(--text-xs)', color: 'var(--fg-tertiary)' }}>
                <span>Filer: <strong style={{ color: 'var(--fg-primary)' }}>{selectedItem.data.evidence.filing_company || 'SEC 10-K'}</strong></span>
                <span>Chunk: <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--fg-secondary)' }}>{selectedItem.data.evidence.chunk_id}</code></span>
              </div>
            </div>
          )}
          {selectedItem.type === 'node' && (
            <p style={{ margin: 0, color: 'var(--fg-secondary)', fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-relaxed)' }}>
              Click an edge to view the supporting evidence quote from the 10-K filing.
            </p>
          )}
        </motion.div>
      )}
    </div>
  );
}