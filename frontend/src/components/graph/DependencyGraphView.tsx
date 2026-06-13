import { useEffect, useState, useCallback } from 'react'
import ReactFlow, {
  Node, Edge, Controls, MiniMap, Background,
  useNodesState, useEdgesState, MarkerType,
  BackgroundVariant,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { reposApi, DependencyGraph } from '../../lib/api'
import { Loader2 } from 'lucide-react'

interface Props { repoId: string }

const LANG_COLORS: Record<string, string> = {
  python: '#3b82f6',
  javascript: '#f59e0b',
  typescript: '#06b6d4',
  unknown: '#6b7280',
}

function buildFlowElements(graph: DependencyGraph): { nodes: Node[]; edges: Edge[] } {
  // Simple force-layout approximation: arrange in grid
  const nodes: Node[] = graph.nodes.map((n, i) => {
    const cols = Math.ceil(Math.sqrt(graph.nodes.length))
    const col = i % cols
    const row = Math.floor(i / cols)
    const color = LANG_COLORS[n.language] ?? LANG_COLORS.unknown

    return {
      id: n.id,
      position: { x: col * 220, y: row * 120 },
      data: {
        label: (
          <div className="px-2 py-1.5 text-left">
            <div className="font-mono text-xs font-medium text-slate-100 truncate max-w-[150px]">{n.label}</div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-slate-500">{n.symbol_count} symbols</span>
              <span className="text-[10px] text-slate-600">{n.line_count}L</span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#1e293b',
        border: `1px solid ${color}40`,
        borderRadius: '8px',
        padding: 0,
        color: 'white',
        borderLeft: `3px solid ${color}`,
        minWidth: 160,
      },
    }
  })

  const edges: Edge[] = graph.edges.map((e, i) => ({
    id: `e-${i}`,
    source: e.source,
    target: e.target,
    label: e.module_name.split('.').pop(),
    style: { stroke: '#475569', strokeWidth: 1 },
    labelStyle: { fill: '#64748b', fontSize: 9 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#475569', width: 12, height: 12 },
    animated: false,
  }))

  return { nodes, edges }
}

export function DependencyGraphView({ repoId }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({ nodes: 0, edges: 0 })

  useEffect(() => {
    reposApi.graph(repoId).then(res => {
      const { nodes: n, edges: e } = buildFlowElements(res.data)
      setNodes(n)
      setEdges(e)
      setStats({ nodes: res.data.nodes.length, edges: res.data.edges.length })
    }).finally(() => setLoading(false))
  }, [repoId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 size={20} className="animate-spin text-brand-400" />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4 text-xs text-slate-500">
        <span>{stats.nodes} files</span>
        <span>{stats.edges} internal imports</span>
        {Object.entries(LANG_COLORS).filter(([k]) => k !== 'unknown').map(([lang, color]) => (
          <span key={lang} className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full" style={{ background: color }} />
            {lang}
          </span>
        ))}
      </div>
      <div className="h-[520px] rounded-xl overflow-hidden border border-slate-800">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          attributionPosition="bottom-left"
        >
          <Controls className="!bg-surface-900 !border-slate-700" />
          <MiniMap
            className="!bg-surface-900 !border-slate-700"
            nodeColor="#334155"
            maskColor="rgba(8,15,30,0.7)"
          />
          <Background variant={BackgroundVariant.Dots} color="#1e293b" gap={20} />
        </ReactFlow>
      </div>
      <p className="text-xs text-slate-600">
        Nodes = source files. Edges = internal imports. Left border color = language.
      </p>
    </div>
  )
}
