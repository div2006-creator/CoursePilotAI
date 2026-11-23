import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Award,
  BrainCircuit,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Compass,
  History,
  Layers,
  Loader2,
  RefreshCw,
  Sparkles,
  Target,
  Zap,
} from 'lucide-react';
import {
  analyzeKnowledgeGaps,
  getKnowledgeGapHistory,
  getKnowledgeGaps,
  reassessPrerequisites,
} from '../services/knowledgeGapService';
import { getCourseById } from '../services/courseService';
import {
  Course,
  GapRecommendationItem,
  KnowledgeGapAnalysisData,
  KnowledgeGapHistoryItem,
  KnowledgeGapType,
  PrerequisiteNode,
} from '../types';
import { extractApiErrorMessage } from '../services/api';

export const KnowledgeGaps: React.FC = () => {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();

  const [course, setCourse] = useState<Course | null>(null);
  const [analysis, setAnalysis] = useState<KnowledgeGapAnalysisData | null>(null);
  const [history, setHistory] = useState<KnowledgeGapHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isReassessing, setIsReassessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [isHistoryExpanded, setIsHistoryExpanded] = useState(false);

  // Load latest knowledge gaps and course info
  const loadData = useCallback(async () => {
    if (!courseId) return;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const [courseRes, analysisRes, historyRes] = await Promise.all([
        getCourseById(courseId),
        getKnowledgeGaps(courseId).catch((err) => {
          // If 404, we will try to run analyze
          if (err?.response?.status === 404) {
            return null;
          }
          throw err;
        }),
        getKnowledgeGapHistory(courseId).catch(() => []),
      ]);

      setCourse(courseRes.data);
      setHistory(historyRes || []);

      if (analysisRes) {
        setAnalysis(analysisRes);
      } else {
        // Trigger initial analysis automatically if none exists yet
        const initialAnalysis = await analyzeKnowledgeGaps(courseId);
        setAnalysis(initialAnalysis);
      }
    } catch (err) {
      setErrorMessage(
        extractApiErrorMessage(err, 'Failed to load knowledge gap intelligence.')
      );
    } finally {
      setIsLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Handler to trigger a fresh analysis run
  const handleRunAnalysis = async () => {
    if (!courseId) return;
    setIsAnalyzing(true);
    setErrorMessage(null);
    try {
      const res = await analyzeKnowledgeGaps(courseId);
      setAnalysis(res);
      const historyRes = await getKnowledgeGapHistory(courseId).catch(() => []);
      setHistory(historyRes || []);
    } catch (err) {
      setErrorMessage(
        extractApiErrorMessage(err, 'Failed to run fresh knowledge gap analysis.')
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handler to trigger targeted reassessment of unassessed prerequisites
  const handleReassessPrerequisites = async () => {
    if (!courseId) return;
    setIsReassessing(true);
    setErrorMessage(null);
    try {
      const sessionData = await reassessPrerequisites(courseId, {
        difficulty: 'mixed',
        questions_per_topic: 2,
      });

      // Navigate to Diagnostic page passing the new sessionData in location.state
      navigate(`/courses/${courseId}/diagnostic`, {
        state: { sessionData },
      });
    } catch (err) {
      setErrorMessage(
        extractApiErrorMessage(
          err,
          'No unassessed prerequisites available for reassessment, or all prerequisites are already evaluated.'
        )
      );
    } finally {
      setIsReassessing(false);
    }
  };

  const getGapTypeBadge = (gapType: KnowledgeGapType) => {
    switch (gapType) {
      case 'foundational_weakness':
        return {
          label: 'Foundational Weakness',
          description: 'Root cause is a failing prerequisite topic',
          className: 'bg-rose-50 text-rose-700 border-rose-200',
          dotColor: 'bg-rose-500',
        };
      case 'direct_weakness':
        return {
          label: 'Direct Topic Weakness',
          description: 'Prerequisites are mastered; weakness is specific to this topic',
          className: 'bg-amber-50 text-amber-700 border-amber-200',
          dotColor: 'bg-amber-500',
        };
      case 'potential_knowledge_gap':
        return {
          label: 'Potential Knowledge Gap',
          description: 'Prerequisite has not been assessed yet',
          className: 'bg-indigo-50 text-indigo-700 border-indigo-200',
          dotColor: 'bg-indigo-500',
        };
      case 'isolated_difficulty':
      default:
        return {
          label: 'Isolated Difficulty',
          description: 'Independent topic with no failing prerequisites',
          className: 'bg-orange-50 text-orange-700 border-orange-200',
          dotColor: 'bg-orange-500',
        };
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'strong':
        return {
          label: 'Strong',
          badge: 'bg-emerald-100 text-emerald-800 border-emerald-200',
        };
      case 'developing':
        return {
          label: 'Developing',
          badge: 'bg-amber-100 text-amber-800 border-amber-200',
        };
      case 'weak':
        return {
          label: 'Weak',
          badge: 'bg-rose-100 text-rose-800 border-rose-200',
        };
      default:
        return {
          label: 'Unassessed',
          badge: 'bg-slate-100 text-slate-700 border-slate-200',
        };
    }
  };

  const getActionBadge = (actionType: string) => {
    switch (actionType) {
      case 'revise_prerequisite':
        return {
          label: 'Revise Prerequisite',
          className: 'bg-rose-100 text-rose-700 border-rose-200',
        };
      case 'practice_topic':
        return {
          label: 'Targeted Practice',
          className: 'bg-amber-100 text-amber-700 border-amber-200',
        };
      case 'take_diagnostic':
      default:
        return {
          label: 'Take Diagnostic',
          className: 'bg-indigo-100 text-indigo-700 border-indigo-200',
        };
    }
  };

  // Filtered gaps list
  const filteredGaps = (analysis?.gaps || []).filter((gap) => {
    if (activeFilter === 'all') return true;
    return gap.gap_type === activeFilter;
  });

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center">
        <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <h2 className="text-xl font-bold text-gray-900">
          Analyzing Prerequisite Knowledge Graph...
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Tracing causal prerequisite chains and assessing foundational weaknesses
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Navigation and Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <Link
            to={courseId ? `/courses/${courseId}` : '/courses'}
            className="inline-flex items-center space-x-1.5 text-xs font-medium text-gray-500 hover:text-indigo-600 transition-colors mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to {course?.title || 'Course'}</span>
          </Link>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
              Knowledge Gap Analysis & Prerequisite Intelligence
            </h1>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
              <BrainCircuit className="w-3 h-3 mr-1 text-indigo-500" />
              Graph BFS Traversal
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Causal root-cause analysis distinguishing surface performance from foundational prerequisite gaps.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={handleRunAnalysis}
            disabled={isAnalyzing}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 transition-colors shadow-sm disabled:opacity-50"
          >
            {isAnalyzing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5 text-indigo-600" />
            )}
            <span>{isAnalyzing ? 'Analyzing...' : 'Re-run Analysis'}</span>
          </button>

          {analysis && analysis.unassessed_topics_count > 0 && (
            <button
              type="button"
              onClick={handleReassessPrerequisites}
              disabled={isReassessing}
              className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50"
            >
              {isReassessing ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Zap className="w-3.5 h-3.5 text-amber-300" />
              )}
              <span>{isReassessing ? 'Starting...' : 'Reassess Unassessed Prerequisites'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div
          role="alert"
          className="flex items-start space-x-2.5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-red-600" />
          <div className="flex-1">
            <p className="font-semibold">Analysis Notice</p>
            <p className="mt-0.5">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Zero Assessment Empty State */}
      {analysis && analysis.assessed_topics === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-12 text-center max-w-xl mx-auto my-8">
          <div className="w-16 h-16 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto mb-4">
            <Award className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-gray-900">
            No Assessment Performance Data Yet
          </h2>
          <p className="mt-2 text-sm text-gray-500 leading-relaxed">
            The Knowledge Gap Engine analyzes your test attempts alongside prerequisite dependencies.
            Take your first diagnostic assessment to uncover hidden foundational gaps.
          </p>
          <div className="mt-6">
            <Link
              to={`/courses/${courseId}/diagnostic`}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-all shadow-md shadow-indigo-100"
            >
              <Award className="w-4 h-4" />
              <span>Take Diagnostic Assessment</span>
            </Link>
          </div>
        </div>
      ) : analysis ? (
        <>
          {/* SECTION A: OVERALL LEARNING HEALTH */}
          <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-gray-100 pb-4">
              <div>
                <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                  <Target className="w-4 h-4 text-indigo-600" />
                  Overall Learning Health & Diagnostic Coverage
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Evaluated across {analysis.total_topics} syllabus topics using graph-based causal tracing
                </p>
              </div>

              <span className="text-xs text-gray-400 font-mono">
                Last analyzed: {new Date(analysis.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {/* Overall Gap Score */}
              <div className="col-span-2 md:col-span-1 bg-gradient-to-br from-slate-50 to-indigo-50/30 rounded-xl p-4 border border-indigo-100/60 flex flex-col justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Gap Severity Score
                </span>
                <div className="my-2">
                  <span
                    className={`text-3xl font-extrabold ${
                      analysis.overall_gap_score > 60
                        ? 'text-rose-600'
                        : analysis.overall_gap_score > 30
                        ? 'text-amber-600'
                        : 'text-emerald-600'
                    }`}
                  >
                    {analysis.overall_gap_score.toFixed(1)}
                  </span>
                  <span className="text-xs text-gray-400 font-medium"> / 100</span>
                </div>
                <div className="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      analysis.overall_gap_score > 60
                        ? 'bg-rose-500'
                        : analysis.overall_gap_score > 30
                        ? 'bg-amber-500'
                        : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, analysis.overall_gap_score)}%` }}
                  />
                </div>
              </div>

              {/* Assessed Topics */}
              <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 flex flex-col justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Coverage
                </span>
                <div className="my-2">
                  <span className="text-2xl font-bold text-gray-900">
                    {analysis.assessed_topics}
                  </span>
                  <span className="text-xs text-gray-500"> / {analysis.total_topics}</span>
                </div>
                <p className="text-xs text-slate-500">
                  {Math.round((analysis.assessed_topics / Math.max(1, analysis.total_topics)) * 100)}% Assessed
                </p>
              </div>

              {/* Strong Topics */}
              <div className="bg-emerald-50/50 rounded-xl p-4 border border-emerald-100 flex flex-col justify-between">
                <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">
                  Strong Topics
                </span>
                <div className="my-2">
                  <span className="text-2xl font-bold text-emerald-700">
                    {analysis.strong_topics_count}
                  </span>
                </div>
                <p className="text-xs text-emerald-600">≥75% accuracy</p>
              </div>

              {/* Developing Topics */}
              <div className="bg-amber-50/50 rounded-xl p-4 border border-amber-100 flex flex-col justify-between">
                <span className="text-xs font-semibold text-amber-700 uppercase tracking-wider">
                  Developing
                </span>
                <div className="my-2">
                  <span className="text-2xl font-bold text-amber-700">
                    {analysis.developing_topics_count}
                  </span>
                </div>
                <p className="text-xs text-amber-600">50% - 74% accuracy</p>
              </div>

              {/* Weak Topics */}
              <div className="bg-rose-50/50 rounded-xl p-4 border border-rose-100 flex flex-col justify-between">
                <span className="text-xs font-semibold text-rose-700 uppercase tracking-wider">
                  Weak Topics
                </span>
                <div className="my-2">
                  <span className="text-2xl font-bold text-rose-700">
                    {analysis.weak_topics_count}
                  </span>
                </div>
                <p className="text-xs text-rose-600">&lt;50% accuracy</p>
              </div>
            </div>

            {/* AI Executive Summary Card */}
            {analysis.summary && (
              <div className="bg-gradient-to-r from-indigo-50/60 via-purple-50/30 to-white rounded-xl p-4 border border-indigo-100 flex items-start space-x-3">
                <div className="p-2 rounded-lg bg-indigo-100 text-indigo-600 flex-shrink-0 mt-0.5">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div className="flex-1">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-900">
                    Academic Diagnostic Summary
                  </h3>
                  <p className="mt-1 text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                    {analysis.summary}
                  </p>
                </div>
              </div>
            )}
          </section>

          {/* SECTION B & C: WEAK TOPIC ANALYSIS & PREREQUISITE CHAINS */}
          <section className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-gray-900 tracking-tight flex items-center gap-2">
                  <Layers className="w-5 h-5 text-indigo-600" />
                  Identified Knowledge Gaps ({analysis.gaps.length})
                </h2>
                <p className="text-xs text-gray-500">
                  Prerequisite DAG inspection reveals whether difficulties stem from foundational prerequisites or isolated concepts.
                </p>
              </div>

              {/* Classification Filter Tabs */}
              <div className="flex flex-wrap items-center gap-1.5 bg-gray-100 p-1 rounded-lg">
                {[
                  { id: 'all', label: `All (${analysis.gaps.length})` },
                  {
                    id: 'foundational_weakness',
                    label: `Foundational (${analysis.gaps.filter((g) => g.gap_type === 'foundational_weakness').length})`,
                  },
                  {
                    id: 'direct_weakness',
                    label: `Direct (${analysis.gaps.filter((g) => g.gap_type === 'direct_weakness').length})`,
                  },
                  {
                    id: 'potential_knowledge_gap',
                    label: `Potential (${analysis.gaps.filter((g) => g.gap_type === 'potential_knowledge_gap').length})`,
                  },
                  {
                    id: 'isolated_difficulty',
                    label: `Isolated (${analysis.gaps.filter((g) => g.gap_type === 'isolated_difficulty').length})`,
                  },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveFilter(tab.id)}
                    className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-colors ${
                      activeFilter === tab.id
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {filteredGaps.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
                <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
                <h3 className="text-base font-semibold text-gray-900">
                  No Knowledge Gaps in this Category
                </h3>
                <p className="text-xs text-gray-500 mt-1">
                  All assessed topics in this category satisfy mastery and prerequisite expectations.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {filteredGaps.map((gap) => {
                  const meta = getGapTypeBadge(gap.gap_type);

                  return (
                    <div
                      key={gap.topic_id}
                      className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4 hover:border-indigo-200 transition-colors"
                    >
                      {/* Gap Card Header */}
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="text-base font-bold text-gray-900">
                              {gap.topic_name}
                            </h3>
                            <span
                              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${meta.className}`}
                            >
                              <span className={`w-1.5 h-1.5 rounded-full ${meta.dotColor}`} />
                              {meta.label}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {meta.description}
                          </p>
                        </div>

                        {/* Metric Pills */}
                        <div className="flex flex-wrap items-center gap-2 text-xs">
                          <span className="px-2.5 py-1 bg-slate-100 rounded-lg font-medium text-slate-700">
                            Accuracy:{' '}
                            <strong className="text-rose-600">
                              {gap.accuracy_percentage.toFixed(0)}%
                            </strong>
                          </span>
                          <span className="px-2.5 py-1 bg-slate-100 rounded-lg font-medium text-slate-700">
                            Attempts: <strong>{gap.attempt_count}</strong>
                          </span>
                          <span className="px-2.5 py-1 bg-slate-100 rounded-lg font-medium text-slate-700">
                            Severity: <strong>{gap.severity.toFixed(1)}/100</strong>
                          </span>
                          <span className="px-2.5 py-1 bg-slate-100 rounded-lg font-medium text-slate-700">
                            Confidence: <strong>{Math.round(gap.confidence * 100)}%</strong>
                          </span>
                        </div>
                      </div>

                      {/* SECTION C: PREREQUISITE DEPENDENCY CHAIN VISUALIZER */}
                      <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-100">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                            <BrainCircuit className="w-3.5 h-3.5 text-indigo-600" />
                            Prerequisite Dependency Chain
                          </span>
                          <span className="text-[11px] text-slate-400">
                            Dependencies traced upwards via DAG
                          </span>
                        </div>

                        {gap.prerequisite_chain.length === 0 ? (
                          <p className="text-xs text-slate-400 italic">
                            No prerequisites declared in syllabus graph. Topic stands alone.
                          </p>
                        ) : (
                          <div className="flex flex-wrap items-center gap-2 pt-1">
                            {gap.prerequisite_chain.map((node: PrerequisiteNode, idx: number) => {
                              const nodeStatus = getStatusBadge(node.knowledge_status);
                              const isTargetNode = node.topic_id === gap.topic_id;

                              return (
                                <React.Fragment key={node.topic_id}>
                                  <div
                                    className={`inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs shadow-2xs ${
                                      isTargetNode
                                        ? 'bg-rose-50 border-rose-300 ring-2 ring-rose-200'
                                        : 'bg-white border-slate-200'
                                    }`}
                                  >
                                    <span className="font-semibold text-slate-900">
                                      {node.topic_name}
                                    </span>
                                    <span
                                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${nodeStatus.badge}`}
                                    >
                                      {nodeStatus.label} ({node.accuracy_percentage.toFixed(0)}%)
                                    </span>
                                    {isTargetNode && (
                                      <span className="text-[10px] uppercase font-bold text-rose-600">
                                        [Target]
                                      </span>
                                    )}
                                  </div>

                                  {idx < gap.prerequisite_chain.length - 1 && (
                                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                                  )}
                                </React.Fragment>
                              );
                            })}
                          </div>
                        )}
                      </div>

                      {/* Recommendation & Evidence Note */}
                      {gap.recommendation && (
                        <div className="text-xs text-slate-700 bg-amber-50/60 border border-amber-100 rounded-lg p-3 flex items-start space-x-2">
                          <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <span className="font-semibold text-amber-900">
                              System Advice:{' '}
                            </span>
                            <span>{gap.recommendation}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* SECTION D: ACTIONABLE RECOMMENDATIONS */}
          {analysis.recommendations && analysis.recommendations.length > 0 && (
            <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-4">
              <div className="border-b border-gray-100 pb-3">
                <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Prioritized Action Plan
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Targeted, deduplicated steps ordered by gap severity to accelerate learning recovery.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {analysis.recommendations.map((rec: GapRecommendationItem) => {
                  const actionMeta = getActionBadge(rec.action_type);

                  return (
                    <div
                      key={`${rec.priority}-${rec.topic_id}`}
                      className="border border-gray-200 rounded-xl p-4 bg-slate-50/50 hover:bg-white hover:border-indigo-200 transition-all flex flex-col justify-between space-y-2"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center space-x-2">
                          <span className="w-5 h-5 rounded-full bg-slate-900 text-white text-[11px] font-bold flex items-center justify-center">
                            #{rec.priority}
                          </span>
                          <h4 className="text-sm font-bold text-gray-900">
                            {rec.topic_name}
                          </h4>
                        </div>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold border ${actionMeta.className}`}
                        >
                          {actionMeta.label}
                        </span>
                      </div>

                      <p className="text-xs text-gray-600 leading-relaxed">
                        {rec.reason}
                      </p>

                      <div className="pt-2 border-t border-gray-100 flex items-center justify-between text-[11px] text-gray-400">
                        <span>Severity: {rec.severity.toFixed(1)}</span>
                        <Link
                          to={`/courses/${courseId}/diagnostic`}
                          className="text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center space-x-1"
                        >
                          <span>Practice Topic</span>
                          <ChevronRight className="w-3 h-3" />
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Part 9: Adaptive Study Plan Bridge CTA */}
              <div className="mt-5 p-5 rounded-2xl bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center space-x-1.5 text-xs font-bold uppercase text-indigo-700 tracking-wider">
                    <Compass className="w-4 h-4 text-indigo-600" />
                    <span>Adaptive Study Plan</span>
                  </div>
                  <h4 className="text-sm font-bold text-gray-900">
                    Ready to resolve these prerequisite gaps?
                  </h4>
                  <p className="text-xs text-gray-600">
                    Convert these prioritized recommendations into a personalized, prerequisite-respecting study schedule.
                  </p>
                </div>
                <Link
                  to={`/courses/${courseId}/study-plan`}
                  className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors flex-shrink-0"
                >
                  <Calendar className="w-3.5 h-3.5 text-amber-300" />
                  <span>Generate / View Study Plan</span>
                </Link>
              </div>
            </section>
          )}

          {/* SECTION E: TARGETED REASSESSMENT CTA */}
          {analysis.unassessed_topics_count > 0 && (
            <section className="bg-gradient-to-r from-indigo-900 to-indigo-800 rounded-2xl shadow-md p-6 text-white flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="space-y-1 max-w-xl">
                <div className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-700/60 text-indigo-200 border border-indigo-500/40">
                  <Zap className="w-3 h-3 text-amber-300" />
                  <span>Targeted Prerequisite Evaluation</span>
                </div>
                <h3 className="text-lg font-bold">
                  Assess Missing Foundational Prerequisites
                </h3>
                <p className="text-xs text-indigo-200 leading-relaxed">
                  You have {analysis.unassessed_topics_count} unassessed prerequisite topic(s).
                  Testing these foundational topics removes diagnostic blindspots and determines if they are the true cause of advanced topic struggles.
                </p>
              </div>

              <button
                type="button"
                onClick={handleReassessPrerequisites}
                disabled={isReassessing}
                className="inline-flex items-center space-x-2 px-5 py-3 rounded-xl text-xs font-bold text-indigo-900 bg-white hover:bg-indigo-50 transition-colors shadow-lg disabled:opacity-75 flex-shrink-0"
              >
                {isReassessing ? (
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                ) : (
                  <Award className="w-4 h-4 text-indigo-600" />
                )}
                <span>{isReassessing ? 'Generating Assessment...' : 'Start Targeted Prerequisite Test'}</span>
              </button>
            </section>
          )}

          {/* SECTION F: HISTORICAL ANALYSES */}
          <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-4">
            <button
              type="button"
              onClick={() => setIsHistoryExpanded(!isHistoryExpanded)}
              className="w-full flex items-center justify-between text-left focus:outline-none"
            >
              <div className="flex items-center space-x-2">
                <History className="w-4 h-4 text-slate-500" />
                <h3 className="text-sm font-bold text-gray-900">
                  Analysis History ({history.length})
                </h3>
              </div>
              <ChevronDown
                className={`w-4 h-4 text-gray-500 transition-transform ${
                  isHistoryExpanded ? 'transform rotate-180' : ''
                }`}
              />
            </button>

            {isHistoryExpanded && (
              <div className="pt-2 border-t border-gray-100">
                {history.length === 0 ? (
                  <p className="text-xs text-gray-400 italic">No historical runs recorded.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 text-xs">
                      <thead>
                        <tr className="text-left text-gray-500 font-semibold uppercase tracking-wider">
                          <th className="py-2 px-3">Date</th>
                          <th className="py-2 px-3">Overall Gap Score</th>
                          <th className="py-2 px-3">Weak Topics Count</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 text-gray-700">
                        {history.map((item) => (
                          <tr key={item.analysis_id} className="hover:bg-gray-50">
                            <td className="py-2 px-3 font-mono">
                              {new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString()}
                            </td>
                            <td className="py-2 px-3 font-semibold">
                              {item.overall_gap_score.toFixed(1)} / 100
                            </td>
                            <td className="py-2 px-3">
                              <span className="px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200 font-semibold">
                                {item.weak_topics_count} weak
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
};

export default KnowledgeGaps;
