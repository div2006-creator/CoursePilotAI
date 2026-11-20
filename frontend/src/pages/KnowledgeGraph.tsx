import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import cytoscape, { Core, EventObject } from 'cytoscape';
import dagre from 'cytoscape-dagre';
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Compass,
  GitFork,
  Layers,
  Loader2,
  Maximize2,
  Pencil,
  RefreshCw,
  Sparkles,
  X,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { TopicDetail, TopicGraphData, TopicGraphNode, TopicUpdatePayload } from '../types';
import { topicService } from '../services/topicService';
import { courseService } from '../services/courseService';
import { extractApiErrorMessage } from '../services/api';
import { EditTopicModal } from '../components/topic';

// Register cytoscape-dagre plugin
try {
  cytoscape.use(dagre);
} catch {
  // Plugin already mounted
}

export const KnowledgeGraph: React.FC = () => {
  const { courseId } = useParams<{ courseId: string }>();

  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const [courseTitle, setCourseTitle] = useState('Course');
  const [graphData, setGraphData] = useState<TopicGraphData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<TopicGraphNode | null>(null);
  const [selectedTopicDetail, setSelectedTopicDetail] = useState<TopicDetail | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [editingTopic, setEditingTopic] = useState<TopicDetail | null>(null);
  const [layoutName, setLayoutName] = useState<'dagre' | 'breadthfirst'>('dagre');

  const fetchGraph = useCallback(async () => {
    if (!courseId) return;
    setIsLoading(true);
    setLoadError(null);
    try {
      const [courseRes, graphRes] = await Promise.all([
        courseService.getCourseById(courseId),
        topicService.getTopicGraph(courseId),
      ]);
      setCourseTitle(courseRes.data.title);
      setGraphData(graphRes.data);
    } catch (err) {
      setLoadError(
        extractApiErrorMessage(err, 'Failed to load knowledge graph data.')
      );
    } finally {
      setIsLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    void fetchGraph();
  }, [fetchGraph]);

  // Load detailed topic info when a node is selected
  useEffect(() => {
    if (!selectedNode) {
      setSelectedTopicDetail(null);
      return;
    }
    let isMounted = true;
    setIsDetailLoading(true);

    topicService
      .getTopicById(selectedNode.id)
      .then((res) => {
        if (isMounted) setSelectedTopicDetail(res.data);
      })
      .catch(() => {
        if (isMounted) setSelectedTopicDetail(null);
      })
      .finally(() => {
        if (isMounted) setIsDetailLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedNode]);

  // Initialize or update Cytoscape graph
  useEffect(() => {
    if (!containerRef.current || !graphData || graphData.nodes.length === 0) {
      return;
    }

    // Destroy existing instance before creating a new one
    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const elements: cytoscape.ElementDefinition[] = [
      ...graphData.nodes.map((node) => ({
        data: {
          id: node.id,
          label: node.label,
          difficulty: node.difficulty || 'medium',
          unit: node.unit || 'General',
          sourceType: node.source_type,
          nodeRaw: node,
        },
      })),
      ...graphData.edges.map((edge, idx) => ({
        data: {
          id: `e_${edge.source}_${edge.target}_${idx}`,
          source: edge.source,
          target: edge.target,
          confidence: `${Math.round(edge.confidence * 100)}%`,
          edgeRaw: edge,
        },
      })),
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      boxSelectionEnabled: false,
      autounselectify: false,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'font-family': 'Inter, system-ui, sans-serif',
            'font-size': '12px',
            'font-weight': 600,
            color: '#1F2937',
            'text-valign': 'center',
            'text-halign': 'center',
            'text-wrap': 'wrap',
            'text-max-width': '140px',
            shape: 'round-rectangle',
            width: 'label',
            height: 'label',
            padding: '12px',
            'background-color': '#FFFFFF',
            'border-width': '2px',
            'border-color': '#6366F1',
            'transition-property': 'background-color, border-color',
            'transition-duration': 150,
          },
        },
        {
          selector: 'node[difficulty = "easy"]',
          style: {
            'background-color': '#ECFDF5',
            'border-color': '#10B981',
            color: '#065F46',
          },
        },
        {
          selector: 'node[difficulty = "medium"]',
          style: {
            'background-color': '#FFFBEB',
            'border-color': '#F59E0B',
            color: '#92400E',
          },
        },
        {
          selector: 'node[difficulty = "hard"]',
          style: {
            'background-color': '#FEF2F2',
            'border-color': '#EF4444',
            color: '#991B1B',
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': '3px',
            'border-color': '#4F46E5',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 2,
            'line-color': '#94A3B8',
            'target-arrow-color': '#64748B',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 1.2,
            label: 'data(confidence)',
            'font-size': '9px',
            'font-weight': 600,
            color: '#64748B',
            'text-background-color': '#FFFFFF',
            'text-background-opacity': 0.85,
            'text-background-padding': '2px',
            'text-background-shape': 'roundrectangle',
          },
        },
        {
          selector: 'edge:selected',
          style: {
            width: 3,
            'line-color': '#4F46E5',
            'target-arrow-color': '#4F46E5',
          },
        },
      ],
    });

    const runLayout = (name: 'dagre' | 'breadthfirst') => {
      if (name === 'dagre') {
        cy.layout({
          name: 'dagre',
          // Directed top-down or left-to-right hierarchy
          rankDir: 'TB',
          nodeSep: 60,
          rankSep: 80,
          animate: true,
          animationDuration: 400,
        } as any).run();
      } else {
        cy.layout({
          name: 'breadthfirst',
          directed: true,
          padding: 30,
          spacingFactor: 1.2,
          animate: true,
          animationDuration: 400,
        }).run();
      }
    };

    runLayout(layoutName);

    // Event listeners
    cy.on('tap', 'node', (evt: EventObject) => {
      const node = evt.target;
      const raw = node.data('nodeRaw') as TopicGraphNode;
      setSelectedNode(raw);
    });

    cy.on('tap', (evt: EventObject) => {
      if (evt.target === cy) {
        setSelectedNode(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [graphData, layoutName]);

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.25);
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 0.8);
    }
  };

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 40);
    }
  };

  const handleUpdateTopic = async (payload: TopicUpdatePayload) => {
    if (!editingTopic) return;
    await topicService.updateTopic(editingTopic.id, payload);
    setEditingTopic(null);
    await fetchGraph();
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link
            to={`/courses/${courseId}/topics`}
            className="inline-flex items-center space-x-1.5 text-xs font-medium text-gray-500 hover:text-indigo-600 transition-colors mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Syllabus Topics</span>
          </Link>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
              Knowledge Graph
            </h1>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-100">
              {courseTitle}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Interactive Directed Acyclic Graph (DAG) displaying prerequisite relationships between topics.
          </p>
        </div>

        <div className="flex items-center space-x-3 self-start sm:self-auto">
          <Link
            to={`/courses/${courseId}/topics`}
            className="inline-flex items-center space-x-1.5 rounded-lg border border-gray-300 bg-white px-3.5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors shadow-sm"
          >
            <Layers className="w-4 h-4 text-indigo-600" />
            <span>Topic List</span>
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 flex flex-col items-center justify-center text-center shadow-sm">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          <p className="mt-3 text-sm font-medium text-gray-700">Loading topic knowledge graph...</p>
        </div>
      ) : loadError ? (
        <div className="bg-white rounded-xl border border-red-200 p-8 text-center max-w-xl mx-auto shadow-sm">
          <AlertCircle className="w-7 h-7 text-red-600 mx-auto" />
          <h2 className="mt-3 text-base font-semibold text-gray-900">Failed to load graph</h2>
          <p className="mt-1 text-sm text-gray-500">{loadError}</p>
          <button
            type="button"
            onClick={() => void fetchGraph()}
            className="mt-4 inline-flex items-center space-x-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Try Again</span>
          </button>
        </div>
      ) : !graphData || graphData.nodes.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm max-w-xl mx-auto">
          <div className="mx-auto w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <GitFork className="w-6 h-6" />
          </div>
          <h2 className="mt-4 text-lg font-semibold text-gray-900">Knowledge Graph is Empty</h2>
          <p className="mt-1.5 text-sm text-gray-500 leading-relaxed">
            Extract syllabus topics first so the system can generate prerequisite nodes and directed edges.
          </p>
          <Link
            to={`/courses/${courseId}/topics`}
            className="mt-5 inline-flex items-center space-x-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700"
          >
            <Sparkles className="w-4 h-4 text-amber-300" />
            <span>Go to Topics & Extract</span>
          </Link>
        </div>
      ) : (
        <div className="relative bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col">
          {/* Controls Bar & Legend */}
          <div className="bg-gray-50/90 border-b border-gray-200 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center space-x-4">
              <span className="font-semibold text-gray-700">Direction:</span>
              <span className="flex items-center space-x-1 text-gray-600">
                <span className="font-medium text-indigo-600">Prerequisite</span>
                <ArrowRight className="w-3.5 h-3.5 text-gray-400" />
                <span className="font-medium text-gray-900">Dependent Topic</span>
              </span>
              <span className="text-gray-300">|</span>
              <div className="flex items-center space-x-3">
                <span className="inline-flex items-center space-x-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  <span>Easy</span>
                </span>
                <span className="inline-flex items-center space-x-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                  <span>Medium</span>
                </span>
                <span className="inline-flex items-center space-x-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                  <span>Hard</span>
                </span>
              </div>
            </div>

            <div className="flex items-center space-x-1.5">
              <button
                type="button"
                onClick={() => setLayoutName((prev) => (prev === 'dagre' ? 'breadthfirst' : 'dagre'))}
                title="Switch graph layout algorithm"
                className="px-2.5 py-1 rounded bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 font-medium transition-colors"
              >
                Layout: {layoutName === 'dagre' ? 'Hierarchical (Dagre)' : 'Breadthfirst'}
              </button>
              <button
                type="button"
                onClick={handleZoomIn}
                title="Zoom in"
                className="p-1.5 rounded bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 transition-colors"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={handleZoomOut}
                title="Zoom out"
                className="p-1.5 rounded bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 transition-colors"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={handleFit}
                title="Fit to screen"
                className="p-1.5 rounded bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 transition-colors"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Graph Viewport and Side Drawer */}
          <div className="relative w-full h-[600px] flex">
            <div
              ref={containerRef}
              className="flex-1 h-full w-full bg-slate-50/50 cursor-grab active:cursor-grabbing"
            />

            {/* Selected Node Details Drawer */}
            {selectedNode && (
              <aside
                className="w-80 md:w-96 border-l border-gray-200 bg-white p-5 overflow-y-auto shadow-lg z-10 space-y-4"
                aria-label="Topic details"
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wider block">
                      {selectedNode.unit || 'Topic Detail'}
                    </span>
                    <h2 className="text-lg font-bold text-gray-900 leading-snug">
                      {selectedNode.label}
                    </h2>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedNode(null)}
                    className="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex flex-wrap gap-2 text-xs">
                  <span
                    className={`px-2 py-0.5 rounded-full font-medium border ${
                      selectedNode.difficulty === 'easy'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : selectedNode.difficulty === 'hard'
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : 'bg-amber-50 text-amber-700 border-amber-200'
                    }`}
                  >
                    Difficulty: {selectedNode.difficulty}
                  </span>
                  <span className="px-2 py-0.5 rounded-full font-medium bg-gray-100 text-gray-700 border border-gray-200">
                    {selectedNode.source_type === 'explicit' ? 'Explicit Syllabus' : 'AI Inferred'}
                  </span>
                </div>

                <div>
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
                    Description
                  </h3>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {selectedNode.description || (
                      <span className="text-gray-400 italic">No description provided.</span>
                    )}
                  </p>
                </div>

                {isDetailLoading ? (
                  <div className="flex items-center space-x-2 text-xs text-gray-500 py-2">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                    <span>Loading relationships...</span>
                  </div>
                ) : selectedTopicDetail ? (
                  <div className="space-y-4 pt-2 border-t border-gray-100 text-xs">
                    <div>
                      <h3 className="font-semibold text-gray-700 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                        <Compass className="w-3.5 h-3.5 text-indigo-600" />
                        <span>Prerequisites Needed ({selectedTopicDetail.prerequisites.length})</span>
                      </h3>
                      {selectedTopicDetail.prerequisites.length === 0 ? (
                        <p className="text-gray-400 italic">No prerequisites required (Foundational topic).</p>
                      ) : (
                        <ul className="space-y-2">
                          {selectedTopicDetail.prerequisites.map((p) => (
                            <li key={p.id} className="p-2 rounded-lg bg-gray-50 border border-gray-100 space-y-0.5">
                              <div className="flex items-center justify-between">
                                <span className="font-semibold text-gray-900">{p.name}</span>
                                <span className="text-indigo-600 font-medium">
                                  {Math.round(p.confidence * 100)}% conf
                                </span>
                              </div>
                              {p.reason && <p className="text-gray-500 text-[11px]">{p.reason}</p>}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <div>
                      <h3 className="font-semibold text-gray-700 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                        <ArrowRight className="w-3.5 h-3.5 text-indigo-600" />
                        <span>Unlocks Topics ({selectedTopicDetail.dependents.length})</span>
                      </h3>
                      {selectedTopicDetail.dependents.length === 0 ? (
                        <p className="text-gray-400 italic">No downstream dependencies.</p>
                      ) : (
                        <ul className="space-y-2">
                          {selectedTopicDetail.dependents.map((d) => (
                            <li key={d.id} className="p-2 rounded-lg bg-gray-50 border border-gray-100 space-y-0.5">
                              <div className="flex items-center justify-between">
                                <span className="font-semibold text-gray-900">{d.name}</span>
                                <span className="text-indigo-600 font-medium">
                                  {Math.round(d.confidence * 100)}% conf
                                </span>
                              </div>
                              {d.reason && <p className="text-gray-500 text-[11px]">{d.reason}</p>}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    {selectedTopicDetail.subtopics.length > 0 && (
                      <div>
                        <h3 className="font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                          Subtopics ({selectedTopicDetail.subtopics.length})
                        </h3>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedTopicDetail.subtopics.map((s) => (
                            <span key={s.id} className="px-2 py-0.5 rounded bg-gray-100 text-gray-700 text-[11px]">
                              {s.name}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : null}

                <div className="pt-3 border-t border-gray-100">
                  <button
                    type="button"
                    onClick={() => {
                      if (selectedTopicDetail) setEditingTopic(selectedTopicDetail);
                    }}
                    disabled={!selectedTopicDetail}
                    className="w-full inline-flex items-center justify-center space-x-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                    <span>Edit Topic Details</span>
                  </button>
                </div>
              </aside>
            )}
          </div>
        </div>
      )}

      {editingTopic && (
        <EditTopicModal
          isOpen={Boolean(editingTopic)}
          topic={editingTopic}
          onClose={() => setEditingTopic(null)}
          onSubmit={handleUpdateTopic}
        />
      )}
    </div>
  );
};

export default KnowledgeGraph;
