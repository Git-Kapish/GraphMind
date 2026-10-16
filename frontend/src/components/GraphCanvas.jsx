import React, { useState } from 'react';
import { Network, Info } from 'lucide-react';

export default function GraphCanvas({ graphPaths }) {
  const [selectedItem, setSelectedItem] = useState(null);

  if (!graphPaths || graphPaths.length === 0) {
    return (
      <div className="graph-empty-container">
        <Network size={36} className="empty-icon" />
        <h4>No Graph Path Traversed</h4>
        <p>This query was answered purely via vector semantic search or explicit refusal.</p>
      </div>
    );
  }

  // Flatten nodes and edges from all graph paths
  const allNodes = [];
  const allEdges = [];
  const nodeSet = new Set();

  graphPaths.forEach((path, pathIdx) => {
    const nodes = path.nodes || [];
    const relations = path.relations || [];
    const evidence = path.evidence || [];

    nodes.forEach((nodeName) => {
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

        allNodes.push({
          id: nodeName,
          label: nodeName,
          type,
          pathIndex: pathIdx,
        });
      }
    });

    for (let i = 0; i < relations.length; i++) {
      const source = nodes[i];
      const target = nodes[i + 1];
      const rel = relations[i];
      const ev = evidence[i] || evidence[0];

      if (source && target) {
        allEdges.push({
          id: `edge_${pathIdx}_${i}`,
          source,
          target,
          relation: rel,
          evidence: ev,
        });
      }
    }
  });

  // Calculate layout coordinates for SVG visualization
  const width = 640;
  const height = Math.max(220, allNodes.length * 60);
  const startX = 80;
  const endX = width - 80;

  const nodeCoords = {};
  allNodes.forEach((node, idx) => {
    const t = allNodes.length > 1 ? idx / (allNodes.length - 1) : 0.5;
    const x = startX + t * (endX - startX);
    const y = height / 2 + (idx % 2 === 0 ? -35 : 35);
    nodeCoords[node.id] = { x, y };
  });

  const getNodeColor = (type) => {
    switch (type) {
      case 'Company':
        return { fill: '#312E81', stroke: '#818CF8', text: '#C7D2FE' };
      case 'Subsidiary':
        return { fill: '#064E3B', stroke: '#34D399', text: '#A7F3D0' };
      case 'Location':
        return { fill: '#78350F', stroke: '#FBBF24', text: '#FDE68A' };
      default:
        return { fill: '#1E293B', stroke: '#94A3B8', text: '#E2E8F0' };
    }
  };

  return (
    <div className="graph-canvas-wrapper">
      <div className="graph-canvas-header">
        <div className="graph-title-strip">
          <Network size={16} className="text-emerald" />
          <span className="graph-canvas-title">Traversed Knowledge Graph Path ({allNodes.length} Nodes, {allEdges.length} Relations)</span>
        </div>
        <span className="badge badge-graph">Verified Neo4j Traversal</span>
      </div>

      <div className="svg-container">
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="graph-svg">
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="26"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#6EE7B7" />
            </marker>
          </defs>

          {/* Render Relationship Edges */}
          {allEdges.map((edge) => {
            const src = nodeCoords[edge.source];
            const dst = nodeCoords[edge.target];
            if (!src || !dst) return null;

            const midX = (src.x + dst.x) / 2;
            const midY = (src.y + dst.y) / 2;

            return (
              <g
                key={edge.id}
                className="graph-edge-group"
                onClick={() => setSelectedItem({ type: 'edge', data: edge })}
              >
                <line
                  x1={src.x}
                  y1={src.y}
                  x2={dst.x}
                  y2={dst.y}
                  stroke="#10B981"
                  strokeWidth="2.5"
                  strokeDasharray="4,2"
                  markerEnd="url(#arrowhead)"
                  className="edge-line"
                />
                <rect
                  x={midX - 45}
                  y={midY - 12}
                  width="90"
                  height="20"
                  rx="4"
                  fill="#0B132B"
                  stroke="rgba(16, 185, 129, 0.4)"
                  strokeWidth="1"
                />
                <text
                  x={midX}
                  y={midY + 2}
                  textAnchor="middle"
                  fill="#6EE7B7"
                  fontSize="9.5"
                  fontFamily="JetBrains Mono"
                  fontWeight="600"
                >
                  {edge.relation}
                </text>
              </g>
            );
          })}

          {/* Render Entity Nodes */}
          {allNodes.map((node) => {
            const coord = nodeCoords[node.id];
            if (!coord) return null;
            const colors = getNodeColor(node.type);

            return (
              <g
                key={node.id}
                className="graph-node-group"
                transform={`translate(${coord.x}, ${coord.y})`}
                onClick={() => setSelectedItem({ type: 'node', data: node })}
              >
                <circle
                  r="20"
                  fill={colors.fill}
                  stroke={colors.stroke}
                  strokeWidth="2.5"
                  className="node-circle"
                />
                <text
                  y="34"
                  textAnchor="middle"
                  fill={colors.text}
                  fontSize="11"
                  fontWeight="600"
                  className="node-label"
                >
                  {node.label.length > 20 ? node.label.slice(0, 18) + '...' : node.label}
                </text>
                <text
                  y="46"
                  textAnchor="middle"
                  fill="#64748B"
                  fontSize="8.5"
                  className="node-type"
                >
                  {node.type}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Selected Node/Edge Detail Strip */}
      {selectedItem && (
        <div className="graph-detail-box fade-in">
          <div className="detail-header">
            <Info size={14} />
            <span>
              {selectedItem.type === 'node'
                ? `Entity: ${selectedItem.data.label} (${selectedItem.data.type})`
                : `Relationship: ${selectedItem.data.relation}`}
            </span>
            <button className="detail-close-btn" onClick={() => setSelectedItem(null)}>×</button>
          </div>
          {selectedItem.type === 'edge' && selectedItem.data.evidence && (
            <div className="detail-content">
              <p className="detail-quote">"{selectedItem.data.evidence.evidence_quote}"</p>
              <div className="detail-meta">
                <span>Filer: <strong>{selectedItem.data.evidence.filing_company || 'SEC 10-K'}</strong></span>
                <span>Chunk: <code>{selectedItem.data.evidence.chunk_id}</code></span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
