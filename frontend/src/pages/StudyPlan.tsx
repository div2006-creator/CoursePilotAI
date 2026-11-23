import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  Calendar,
  Compass,
  History,
  Loader2,
  RefreshCw,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  ArrowLeft,
  CalendarCheck,
  Sliders,
  X,
} from 'lucide-react';
import {
  Course,
  PlanItemStatus,
  StudyPlan as StudyPlanType,
  StudyPlanGeneratePayload,
  StudyPlanHistoryItem,
} from '../types';
import { courseService } from '../services/courseService';
import {
  generateStudyPlan,
  getActiveStudyPlan,
  getStudyPlanById,
  getStudyPlanHistory,
  rebalanceStudyPlan,
  updatePlanItemStatus,
} from '../services/planService';
import { PlanProgress } from '../components/roadmap/PlanProgress';
import { StudyPlanCalendar } from '../components/roadmap/StudyPlanCalendar';
import { StudyPlanCard } from '../components/roadmap/StudyPlanCard';

export const StudyPlan: React.FC = () => {
  const { courseId: routeCourseId } = useParams<{ courseId?: string }>();
  const navigate = useNavigate();

  // State
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>(routeCourseId || '');
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);

  const [plan, setPlan] = useState<StudyPlanType | null>(null);
  const [history, setHistory] = useState<StudyPlanHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isRebalancing, setIsRebalancing] = useState<boolean>(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // View mode: 'calendar' | 'roadmap'
  const [activeTab, setActiveTab] = useState<'calendar' | 'roadmap'>('calendar');

  // Modal / Drawer states
  const [isRegenerateModalOpen, setIsRegenerateModalOpen] = useState(false);
  const [isHistoryDrawerOpen, setIsHistoryDrawerOpen] = useState(false);

  // Generate / Regenerate form fields
  const [dailyMinutesInput, setDailyMinutesInput] = useState<number>(60);
  const [examDateInput, setExamDateInput] = useState<string>('');

  // 1. Load user courses for workspace selection
  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const res = await courseService.getCourses();
        const courseList = res.data.courses;
        setCourses(courseList);

        if (!selectedCourseId && courseList.length > 0) {
          setSelectedCourseId(courseList[0].id);
        }
      } catch (err) {
        console.error('Failed to load courses', err);
      }
    };
    fetchCourses();
  }, []);

  // Update selectedCourse when selectedCourseId changes
  useEffect(() => {
    if (selectedCourseId && courses.length > 0) {
      const found = courses.find((c) => c.id === selectedCourseId) || null;
      setSelectedCourse(found);
      if (found) {
        setDailyMinutesInput(found.daily_minutes || 60);
        setExamDateInput(found.exam_date || '');
      }
    }
  }, [selectedCourseId, courses]);

  // Sync selectedCourseId if URL param changes
  useEffect(() => {
    if (routeCourseId && routeCourseId !== selectedCourseId) {
      setSelectedCourseId(routeCourseId);
    }
  }, [routeCourseId]);

  // 2. Load active study plan for selected course
  const loadPlan = useCallback(
    async (courseId: string) => {
      if (!courseId) return;
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const activePlan = await getActiveStudyPlan(courseId);
        setPlan(activePlan);
      } catch (err: any) {
        // If 404, no plan exists yet for this course
        if (err.response?.status === 404) {
          setPlan(null);
        } else {
          setErrorMessage(
            err.response?.data?.message ||
              err.response?.data?.detail ||
              'Failed to retrieve study plan.'
          );
        }
      } finally {
        setIsLoading(false);
      }

      // Also fetch history
      try {
        const hist = await getStudyPlanHistory(courseId);
        setHistory(hist);
      } catch {
        setHistory([]);
      }
    },
    []
  );

  useEffect(() => {
    if (selectedCourseId) {
      loadPlan(selectedCourseId);
    }
  }, [selectedCourseId, loadPlan]);

  // Handle plan generation
  const handleGenerate = async (forceRegenerate: boolean = false) => {
    if (!selectedCourseId) return;
    setIsGenerating(true);
    setErrorMessage(null);
    try {
      const payload: StudyPlanGeneratePayload = {
        daily_minutes: Number(dailyMinutesInput),
        exam_date: examDateInput ? examDateInput : null,
        force_regenerate: forceRegenerate,
      };
      const generated = await generateStudyPlan(selectedCourseId, payload);
      setPlan(generated);
      setNotice(
        `Personalized Study Plan (v${generated.version}) generated successfully with ${generated.progress.total_items} sessions!`
      );
      setIsRegenerateModalOpen(false);

      // Refresh history
      const hist = await getStudyPlanHistory(selectedCourseId);
      setHistory(hist);
    } catch (err: any) {
      setErrorMessage(
        err.response?.data?.message ||
          err.response?.data?.detail ||
          'Failed to generate study plan. Please ensure syllabus topics are extracted.'
      );
    } finally {
      setIsGenerating(false);
    }
  };

  // Handle dynamic rebalance
  const handleRebalance = async () => {
    if (!plan) return;
    setIsRebalancing(true);
    setErrorMessage(null);
    try {
      const rebalanced = await rebalanceStudyPlan(plan.id);
      setPlan(rebalanced);
      setNotice('Study plan dynamically rebalanced based on your latest mastery and calendar pace.');
    } catch (err: any) {
      setErrorMessage(
        err.response?.data?.message ||
          err.response?.data?.detail ||
          'Failed to rebalance study plan.'
      );
    } finally {
      setIsRebalancing(false);
    }
  };

  // Handle session status update
  const handleUpdateSessionStatus = async (
    sessionId: string,
    newStatus: PlanItemStatus
  ) => {
    if (!plan) return;
    try {
      const updatedItem = await updatePlanItemStatus(plan.id, sessionId, {
        status: newStatus,
      });

      // Optimistically update local plan structure
      setPlan((prev) => {
        if (!prev) return prev;
        const newDays = prev.days.map((d) => ({
          ...d,
          sessions: d.sessions.map((s) => (s.id === sessionId ? updatedItem : s)),
        }));

        // Recompute quick counts
        const allSessions = newDays.flatMap((d) => d.sessions);
        const comp = allSessions.filter((s) => s.status === 'COMPLETED').length;
        const total = allSessions.length;
        const compPct = total > 0 ? Math.round((comp / total) * 100) : 0;
        const compMins = allSessions
          .filter((s) => s.status === 'COMPLETED')
          .reduce((sum, s) => sum + s.duration_minutes, 0);

        return {
          ...prev,
          days: newDays,
          progress: {
            ...prev.progress,
            completed_items: comp,
            completed_minutes: compMins,
            completion_percentage: compPct,
          },
        };
      });
    } catch (err: any) {
      setErrorMessage(
        err.response?.data?.message ||
          err.response?.data?.detail ||
          'Failed to update session status.'
      );
    }
  };

  // View specific historical plan snapshot
  const handleSelectHistoryVersion = async (historyPlanId: string) => {
    setIsLoading(true);
    try {
      const histPlan = await getStudyPlanById(historyPlanId);
      setPlan(histPlan);
      setIsHistoryDrawerOpen(false);
      setNotice(`Viewing Plan snapshot version v${histPlan.version} (${histPlan.status}).`);
    } catch (err: any) {
      setErrorMessage(
        err.response?.data?.message || 'Failed to retrieve historical plan snapshot.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Flatten sessions across all days
  const allSessions = plan ? plan.days.flatMap((d) => d.sessions) : [];

  return (
    <div className="space-y-6">
      {/* Notifications */}
      {notice && (
        <div className="flex items-center justify-between p-3.5 rounded-xl border border-emerald-200 bg-emerald-50 text-emerald-800 text-sm shadow-xs">
          <div className="flex items-center space-x-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{notice}</span>
          </div>
          <button
            type="button"
            onClick={() => setNotice(null)}
            className="p-1 rounded text-emerald-700 hover:bg-emerald-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="flex items-center justify-between p-3.5 rounded-xl border border-red-200 bg-red-50 text-red-800 text-sm shadow-xs">
          <div className="flex items-center space-x-2.5">
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            className="p-1 rounded text-red-700 hover:bg-red-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Top Header & Course Selector Bar */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center space-x-2 text-xs font-semibold text-indigo-600 tracking-wide uppercase">
            <Compass className="w-4 h-4" />
            <span>Adaptive Study Roadmap</span>
          </div>

          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
            {plan ? plan.course_title : selectedCourse ? selectedCourse.title : 'Study Plan'}
          </h1>

          <p className="text-sm text-gray-500">
            Personalized, prerequisite-respecting study schedule tailored to your knowledge gaps.
          </p>
        </div>

        {/* Course Switcher */}
        <div className="flex items-center space-x-3 flex-shrink-0">
          {courses.length > 1 && (
            <div className="relative">
              <select
                value={selectedCourseId}
                onChange={(e) => {
                  setSelectedCourseId(e.target.value);
                  navigate(`/courses/${e.target.value}/study-plan`);
                }}
                className="rounded-lg border border-gray-300 bg-white py-2 pl-3 pr-8 text-sm font-medium text-gray-700 shadow-2xs hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
            </div>
          )}

          {selectedCourseId && (
            <Link
              to={`/courses/${selectedCourseId}`}
              className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors shadow-2xs"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Course Details</span>
            </Link>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-16 text-center shadow-xs">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500 font-medium">Loading personalized study plan...</p>
        </div>
      ) : !plan ? (
        /* Empty State: No Study Plan Generated Yet */
        <div className="bg-white rounded-2xl border border-gray-200 p-10 text-center shadow-xs max-w-2xl mx-auto space-y-6">
          <div className="w-16 h-16 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto shadow-inner">
            <CalendarCheck className="w-8 h-8" />
          </div>

          <div className="space-y-2">
            <h2 className="text-xl font-bold text-gray-900">
              No Active Study Plan for this Course
            </h2>
            <p className="text-sm text-gray-500 leading-relaxed">
              CoursePilot AI analyzes your diagnostic assessments, weak topics, and prerequisite
              dependencies to compute a custom daily schedule that guarantees foundational topics
              are cleared first.
            </p>
          </div>

          {/* Quick Setup Form */}
          <div className="bg-gray-50 rounded-xl p-5 border border-gray-200 text-left space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-600">
              Configure Your Study Preferences
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Daily Available Study Time
                </label>
                <div className="relative">
                  <input
                    type="number"
                    min="15"
                    max="720"
                    step="15"
                    value={dailyMinutesInput}
                    onChange={(e) => setDailyMinutesInput(Math.max(15, Number(e.target.value)))}
                    className="w-full rounded-lg border border-gray-300 py-2 pl-3 pr-12 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <span className="absolute right-3 top-2.5 text-xs text-gray-400 font-medium">
                    min/day
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Target Exam Date (Optional)
                </label>
                <input
                  type="date"
                  value={examDateInput}
                  onChange={(e) => setExamDateInput(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 py-2 px-3 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={() => handleGenerate(false)}
            disabled={isGenerating}
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-3 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-60 transition-all shadow-sm"
          >
            {isGenerating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4 text-amber-300" />
            )}
            <span>{isGenerating ? 'Computing Optimal Schedule...' : 'Generate Personalized Study Plan'}</span>
          </button>
        </div>
      ) : (
        /* Active Study Plan Dashboard */
        <div className="space-y-6">
          {/* Plan Header Bar */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800">
                Plan v{plan.version}
              </span>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase ${
                  plan.status.toLowerCase() === 'active'
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-gray-100 text-gray-700'
                }`}
              >
                {plan.status}
              </span>
              <div className="text-xs text-gray-500 flex items-center space-x-2">
                <span>Daily: {plan.daily_minutes}m</span>
                <span>&bull;</span>
                <span>
                  {plan.exam_date ? `Exam: ${plan.exam_date}` : 'Rolling 7-Day Window'}
                </span>
              </div>
            </div>

            {/* Plan Action CTAs */}
            <div className="flex flex-wrap items-center gap-2.5">
              <button
                type="button"
                onClick={handleRebalance}
                disabled={isRebalancing}
                title="Dynamically adjust remaining sessions from today forward"
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-gray-300 bg-white text-xs font-semibold text-gray-700 hover:bg-gray-50 transition-colors shadow-2xs disabled:opacity-50"
              >
                {isRebalancing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                ) : (
                  <RefreshCw className="w-3.5 h-3.5 text-indigo-600" />
                )}
                <span>Rebalance Plan</span>
              </button>

              <button
                type="button"
                onClick={() => setIsRegenerateModalOpen(true)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-indigo-200 bg-indigo-50 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors shadow-2xs"
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>Adjust / Regenerate</span>
              </button>

              {history.length > 0 && (
                <button
                  type="button"
                  onClick={() => setIsHistoryDrawerOpen(true)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-gray-300 bg-white text-xs font-semibold text-gray-700 hover:bg-gray-50 transition-colors shadow-2xs"
                >
                  <History className="w-3.5 h-3.5 text-gray-500" />
                  <span>History ({history.length})</span>
                </button>
              )}
            </div>
          </div>

          {/* Progress & Health Bar */}
          <PlanProgress progress={plan.progress} />

          {/* View Toggle Tabs */}
          <div className="flex items-center justify-between border-b border-gray-200 pb-2">
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setActiveTab('calendar')}
                className={`inline-flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                  activeTab === 'calendar'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <Calendar className="w-4 h-4" />
                <span>Day-by-Day Schedule</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('roadmap')}
                className={`inline-flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                  activeTab === 'roadmap'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <Compass className="w-4 h-4" />
                <span>Visual Prerequisite Roadmap</span>
              </button>
            </div>

            <span className="text-xs text-gray-500">
              {allSessions.length} total sessions scheduled
            </span>
          </div>

          {/* Tab Content */}
          {activeTab === 'calendar' ? (
            <StudyPlanCalendar
              days={plan.days}
              dailyMinutesTarget={plan.daily_minutes}
              courseId={plan.course_id || selectedCourseId}
              onUpdateSessionStatus={handleUpdateSessionStatus}
            />
          ) : (
            <StudyPlanCard
              sessions={allSessions}
              courseId={plan.course_id || selectedCourseId}
              onUpdateStatus={handleUpdateSessionStatus}
            />
          )}
        </div>
      )}

      {/* Regenerate Plan Modal */}
      {isRegenerateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-gray-900">Adjust & Regenerate Plan</h3>
              <button
                type="button"
                onClick={() => setIsRegenerateModalOpen(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-gray-500">
              Regenerating will archive version v{plan?.version} and create an updated plan
              respecting the latest knowledge gaps and prerequisite graph.
            </p>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Daily Study Limit (Minutes)
                </label>
                <input
                  type="number"
                  min="15"
                  max="720"
                  step="15"
                  value={dailyMinutesInput}
                  onChange={(e) => setDailyMinutesInput(Math.max(15, Number(e.target.value)))}
                  className="w-full rounded-lg border border-gray-300 py-2 px-3 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Target Exam Date
                </label>
                <input
                  type="date"
                  value={examDateInput}
                  onChange={(e) => setExamDateInput(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 py-2 px-3 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-3 border-t border-gray-100">
              <button
                type="button"
                onClick={() => setIsRegenerateModalOpen(false)}
                className="px-4 py-2 rounded-lg text-xs font-semibold text-gray-600 hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleGenerate(true)}
                disabled={isGenerating}
                className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 shadow-xs"
              >
                {isGenerating && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Regenerate Plan (v{(plan?.version || 1) + 1})</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* History Drawer Modal */}
      {isHistoryDrawerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div className="flex items-center space-x-2 text-gray-900 font-bold">
                <History className="w-5 h-5 text-indigo-600" />
                <span>Study Plan Version History</span>
              </div>
              <button
                type="button"
                onClick={() => setIsHistoryDrawerOpen(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="max-h-80 overflow-y-auto space-y-2.5">
              {history.map((h) => (
                <div
                  key={h.id}
                  className={`flex items-center justify-between p-3.5 rounded-xl border transition-colors ${
                    plan?.id === h.id
                      ? 'bg-indigo-50/50 border-indigo-300'
                      : 'bg-white border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-gray-900">
                        Version {h.version}
                      </span>
                      <span
                        className={`text-2xs px-2 py-0.5 rounded-full uppercase font-semibold ${
                          h.status === 'active'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {h.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500">
                      Created on {new Date(h.created_at).toLocaleDateString()} &bull; {h.daily_minutes}m/day
                    </p>
                  </div>

                  <div className="flex items-center space-x-3">
                    <div className="text-right">
                      <span className="text-xs font-bold text-gray-900">
                        {h.completion_percentage}%
                      </span>
                      <p className="text-2xs text-gray-400">
                        {h.completed_items}/{h.total_items} items
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleSelectHistoryVersion(h.id)}
                      className="px-2.5 py-1 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-md border border-indigo-200"
                    >
                      View
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudyPlan;
