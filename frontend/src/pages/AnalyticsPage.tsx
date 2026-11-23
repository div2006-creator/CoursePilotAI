import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  BarChart3,
  RefreshCw,
  BookOpen,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { Course, FullAnalyticsDashboardData } from '../types';
import { courseService } from '../services/courseService';
import { analyticsService } from '../services/analyticsService';
import { extractApiErrorMessage } from '../services/api';
import {
  LearningOverview,
  MasteryDistribution,
  LearningProgressChart,
  TopicMasteryTable,
  ImprovementComparison,
  ExamReadinessCard,
  StudyConsistency,
  BottleneckCard,
  RecommendationList,
} from '../components/dashboard';

type TabKey = 'all' | 'mastery' | 'improvement' | 'readiness' | 'habits';

export const AnalyticsPage: React.FC = () => {
  const { courseId: paramCourseId } = useParams<{ courseId?: string }>();
  const navigate = useNavigate();

  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>(paramCourseId || '');
  const [dashboardData, setDashboardData] = useState<FullAnalyticsDashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('all');

  // 1. Fetch available courses on mount
  useEffect(() => {
    let isMounted = true;
    const loadCourses = async () => {
      try {
        const res = await courseService.getCourses();
        if (isMounted) {
          const list = res.data.courses;
          setCourses(list);
          if (!paramCourseId && list.length > 0) {
            setSelectedCourseId(list[0].id);
          }
        }
      } catch (err) {
        if (isMounted) {
          setError(extractApiErrorMessage(err, 'Failed to load user courses.'));
        }
      }
    };
    void loadCourses();
    return () => {
      isMounted = false;
    };
  }, [paramCourseId]);

  // Synchronize route param with state
  useEffect(() => {
    if (paramCourseId && paramCourseId !== selectedCourseId) {
      setSelectedCourseId(paramCourseId);
    }
  }, [paramCourseId]);

  // 2. Fetch full dashboard analytics when selectedCourseId changes
  const fetchAnalytics = useCallback(async (courseId: string, background = false) => {
    if (!courseId) return;
    if (!background) setIsLoading(true);
    else setIsRefreshing(true);
    setError(null);

    try {
      const res = await analyticsService.getFullAnalyticsDashboard(courseId);
      setDashboardData(res.data);
    } catch (err) {
      setError(extractApiErrorMessage(err, 'Failed to load learning analytics.'));
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCourseId) {
      void fetchAnalytics(selectedCourseId);
    } else {
      setIsLoading(false);
    }
  }, [selectedCourseId, fetchAnalytics]);

  const handleCourseChange = (newCourseId: string) => {
    setSelectedCourseId(newCourseId);
    navigate(`/courses/${newCourseId}/analytics`);
  };

  const currentCourse = courses.find((c) => c.id === selectedCourseId);

  return (
    <div className="space-y-6">
      {/* Top Header & Course Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-gray-100 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center shrink-0">
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Learning Analytics &amp; Intelligence</h1>
            <p className="text-xs text-gray-500">
              Verified retention, longitudinal mastery progression, and adaptive exam readiness
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Course Selector Dropdown */}
          {courses.length > 0 && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-gray-500 font-medium hidden sm:inline">Course:</span>
              <select
                value={selectedCourseId}
                onChange={(e) => handleCourseChange(e.target.value)}
                className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-1.5 text-xs font-semibold text-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {courses.map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.title}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Refresh Button */}
          {selectedCourseId && (
            <button
              onClick={() => void fetchAnalytics(selectedCourseId, true)}
              disabled={isRefreshing || isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 hover:bg-gray-100 text-gray-700 rounded-lg text-xs font-medium border border-gray-200 transition-colors disabled:opacity-50"
              title="Refresh Analytics"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      {dashboardData && !isLoading && (
        <div className="flex flex-wrap items-center gap-2 border-b border-gray-200 pb-2">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'all'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            Full Dashboard
          </button>
          <button
            onClick={() => setActiveTab('mastery')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'mastery'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            Topic Mastery &amp; Status
          </button>
          <button
            onClick={() => setActiveTab('improvement')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'improvement'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            Verified Improvement
          </button>
          <button
            onClick={() => setActiveTab('readiness')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'readiness'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            Exam Readiness
          </button>
          <button
            onClick={() => setActiveTab('habits')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              activeTab === 'habits'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            Consistency &amp; Bottlenecks
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="p-16 flex flex-col items-center justify-center text-center space-y-3 bg-white rounded-2xl border border-gray-100 shadow-sm">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          <p className="text-sm font-semibold text-gray-700">Computing Deterministic Analytics...</p>
          <p className="text-xs text-gray-400">
            Analyzing topic mastery history, fresh test results, and prerequisite graphs
          </p>
        </div>
      )}

      {/* Error Banner */}
      {error && !isLoading && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-3 text-xs text-rose-800">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-rose-900">Analytics Error</p>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Empty State: No Courses */}
      {!isLoading && courses.length === 0 && !error && (
        <div className="p-12 text-center bg-white rounded-2xl border border-gray-100 shadow-sm space-y-4">
          <BookOpen className="w-12 h-12 text-gray-300 mx-auto" />
          <div>
            <h2 className="text-lg font-bold text-gray-900">No Courses Enrolled</h2>
            <p className="text-xs text-gray-500 mt-1">
              Create a course and upload a syllabus to unlock adaptive learning analytics.
            </p>
          </div>
          <Link
            to="/courses"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition-colors"
          >
            <span>Go to Courses</span>
          </Link>
        </div>
      )}

      {/* Main Content Area */}
      {!isLoading && dashboardData && (
        <div className="space-y-6">
          {/* Section A: Always Visible Summary / Overview Header */}
          <LearningOverview
            overview={dashboardData.overview}
            courseTitle={currentCourse?.title}
          />

          {/* Section B: Tab-Dependent Content */}
          {activeTab === 'all' && (
            <div className="space-y-6">
              {/* Mastery Distribution & Exam Readiness Side-by-Side on Desktop */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <MasteryDistribution overview={dashboardData.overview} />
                <ExamReadinessCard data={dashboardData.exam_readiness} />
              </div>

              {/* Longitudinal Progress Chart & Velocity */}
              <LearningProgressChart progress={dashboardData.progress} />

              {/* Verified Post-Learning Improvement Comparison */}
              <ImprovementComparison improvement={dashboardData.improvement} />

              {/* Foundational Prerequisite Bottlenecks */}
              <BottleneckCard
                bottlenecks={dashboardData.bottlenecks}
                courseId={selectedCourseId}
              />

              {/* Prioritized Recommendations */}
              <RecommendationList recommendations={dashboardData.recommendations} />

              {/* Full Topic Mastery Table */}
              <TopicMasteryTable
                data={dashboardData.mastery_analytics}
                courseId={selectedCourseId}
              />

              {/* Study Consistency & Habit Calendar */}
              <StudyConsistency consistency={dashboardData.consistency} />
            </div>
          )}

          {activeTab === 'mastery' && (
            <div className="space-y-6">
              <MasteryDistribution overview={dashboardData.overview} />
              <TopicMasteryTable
                data={dashboardData.mastery_analytics}
                courseId={selectedCourseId}
              />
            </div>
          )}

          {activeTab === 'improvement' && (
            <div className="space-y-6">
              <ImprovementComparison improvement={dashboardData.improvement} />
              <LearningProgressChart progress={dashboardData.progress} />
            </div>
          )}

          {activeTab === 'readiness' && (
            <div className="space-y-6">
              <ExamReadinessCard data={dashboardData.exam_readiness} />
              <RecommendationList recommendations={dashboardData.recommendations} />
            </div>
          )}

          {activeTab === 'habits' && (
            <div className="space-y-6">
              <StudyConsistency consistency={dashboardData.consistency} />
              <BottleneckCard
                bottlenecks={dashboardData.bottlenecks}
                courseId={selectedCourseId}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalyticsPage;
