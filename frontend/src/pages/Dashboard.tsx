import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  BookOpen,
  BrainCircuit,
  Calendar,
  CheckCircle2,
  Clock,
  Loader2,
  Plus,
  RefreshCw,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Course, CourseCreatePayload, CourseUpdatePayload } from '../types';
import { courseService } from '../services/courseService';
import { extractApiErrorMessage } from '../services/api';
import {
  formatCalendarDate,
  formatStudyMinutes,
  getCourseStatusMeta,
  getExamCountdownText,
} from '../utils/courseFormatters';
import { CourseFormModal } from '../components/course';
import { OnboardingGuide } from '../components/common/OnboardingGuide';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [courses, setCourses] = useState<Course[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const fetchCourses = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const response = await courseService.getCourses();
      setCourses(response.data.courses);
    } catch (error) {
      setLoadError(
        extractApiErrorMessage(error, 'Failed to load dashboard data. Please try again.')
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchCourses();
  }, [fetchCourses]);

  const upcomingExams = useMemo(() => {
    return courses
      .filter(
        (course) =>
          course.exam_date !== null &&
          course.days_remaining !== null &&
          course.days_remaining >= 0
      )
      .sort((a, b) => (a.days_remaining ?? 0) - (b.days_remaining ?? 0));
  }, [courses]);

  const totalDailyMinutes = useMemo(() => {
    return courses.reduce((sum, course) => sum + course.daily_minutes, 0);
  }, [courses]);

  const recentCourses = useMemo(() => courses.slice(0, 4), [courses]);

  const nextExam = upcomingExams[0] ?? null;

  const handleCreateCourse = async (
    payload: CourseCreatePayload | CourseUpdatePayload
  ) => {
    const response = await courseService.createCourse(payload as CourseCreatePayload);
    setCourses((prev) => [response.data, ...prev]);
    setIsCreateModalOpen(false);
    setNotice(`Course "${response.data.title}" added to your dashboard.`);
  };

  const firstName = user?.name?.trim().split(/\s+/)[0] || 'Student';

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
            Welcome back, {firstName}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Here is a live summary of your active courses, upcoming exams, and daily study budget.
          </p>
        </div>

        <div className="flex items-center space-x-3 self-start sm:self-auto">
          <Link
            to="/courses"
            className="inline-flex items-center space-x-1.5 rounded-lg border border-gray-300 bg-white px-3.5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <span>All Courses</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center space-x-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>New Course</span>
          </button>
        </div>
      </div>

      {notice && (
        <div
          role="status"
          className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
        >
          <div className="flex items-center space-x-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{notice}</span>
          </div>
          <button
            type="button"
            onClick={() => setNotice(null)}
            aria-label="Dismiss notification"
            className="p-1 rounded text-emerald-700 hover:bg-emerald-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 flex flex-col items-center justify-center text-center">
          <Loader2 className="w-7 h-7 text-indigo-600 animate-spin" />
          <p className="mt-3 text-sm font-medium text-gray-700">Loading your study overview...</p>
        </div>
      ) : loadError ? (
        <div className="bg-white rounded-xl border border-red-200 p-8 text-center">
          <div className="mx-auto w-11 h-11 rounded-full bg-red-50 text-red-600 flex items-center justify-center">
            <AlertCircle className="w-5 h-5" />
          </div>
          <h2 className="mt-3 text-base font-semibold text-gray-900">
            Could not load dashboard summary
          </h2>
          <p className="mt-1 text-sm text-gray-500 max-w-md mx-auto">{loadError}</p>
          <button
            type="button"
            onClick={() => void fetchCourses()}
            className="mt-4 inline-flex items-center space-x-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Try Again</span>
          </button>
        </div>
      ) : (
        <>
          <OnboardingGuide courses={courses} />

          <section className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
                  Total Courses
                </span>
                <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <BookOpen className="w-4 h-4" />
                </div>
              </div>
              <p className="mt-3 text-3xl font-bold text-gray-900">{courses.length}</p>
              <p className="mt-1 text-xs text-gray-500">
                {courses.length === 0
                  ? 'Add your first course to get started'
                  : courses.length === 1
                    ? '1 course in your workspace'
                    : `${courses.length} courses in your workspace`}
              </p>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
                  Upcoming Exams
                </span>
                <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <Calendar className="w-4 h-4" />
                </div>
              </div>
              <p className="mt-3 text-3xl font-bold text-gray-900">{upcomingExams.length}</p>
              <p className="mt-1 text-xs text-gray-500 truncate">
                {nextExam
                  ? `Next: ${nextExam.title} (${getExamCountdownText(nextExam)})`
                  : 'No upcoming exam dates scheduled'}
              </p>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
                  Daily Study Commitment
                </span>
                <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <Clock className="w-4 h-4" />
                </div>
              </div>
              <p className="mt-3 text-3xl font-bold text-gray-900">
                {totalDailyMinutes > 0 ? formatStudyMinutes(totalDailyMinutes) : '0 min'}
              </p>
              <p className="mt-1 text-xs text-gray-500">
                {totalDailyMinutes > 0
                  ? `${totalDailyMinutes} minutes/day across all courses`
                  : 'Set daily study time when creating a course'}
              </p>
            </div>
          </section>

          {courses.length === 0 ? (
            <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center">
              <div className="mx-auto w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <BookOpen className="w-6 h-6" />
              </div>
              <h2 className="mt-4 text-lg font-semibold text-gray-900">
                Set up your first course
              </h2>
              <p className="mt-1.5 text-sm text-gray-500 max-w-md mx-auto">
                Start by adding a subject you want to master, your upcoming exam date, and how
                much time you can study each day.
              </p>
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(true)}
                className="mt-5 inline-flex items-center space-x-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Create Your First Course</span>
              </button>
            </section>
          ) : (
            <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                  <div>
                    <h2 className="text-base font-semibold text-gray-900">
                      Recently Created Courses
                    </h2>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Jump directly into a course to inspect details or adjust study targets.
                    </p>
                  </div>
                  <Link
                    to="/courses"
                    className="text-sm font-medium text-indigo-600 hover:text-indigo-700 inline-flex items-center space-x-1"
                  >
                    <span>View all</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>

                <ul className="divide-y divide-gray-100">
                  {recentCourses.map((course) => {
                    const statusMeta = getCourseStatusMeta(course);
                    return (
                      <li key={course.id}>
                        <Link
                          to={`/courses/${course.id}`}
                          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 px-6 py-4 hover:bg-gray-50 transition-colors"
                        >
                          <div className="min-w-0">
                            <div className="flex items-center space-x-2.5">
                              <span className="text-sm font-semibold text-gray-900 truncate">
                                {course.title}
                              </span>
                              <span
                                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border flex-shrink-0 ${statusMeta.badgeClassName}`}
                              >
                                {statusMeta.label}
                              </span>
                            </div>
                            <p className="mt-1 text-xs text-gray-500 truncate">
                              {course.description || 'No description added yet.'}
                            </p>
                          </div>

                          <div className="flex items-center space-x-3 text-xs text-gray-500 flex-shrink-0">
                            <span className="inline-flex items-center space-x-1">
                              <Clock className="w-3.5 h-3.5 text-gray-400" />
                              <span>{formatStudyMinutes(course.daily_minutes)}/day</span>
                            </span>
                            <span className="inline-flex items-center space-x-1">
                              <Calendar className="w-3.5 h-3.5 text-gray-400" />
                              <span>{formatCalendarDate(course.exam_date)}</span>
                            </span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                navigate(`/courses/${course.id}/knowledge-gaps`);
                              }}
                              className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors"
                              title="Inspect Knowledge Gaps & Prerequisite Analysis"
                            >
                              <BrainCircuit className="w-3 h-3 text-indigo-600" />
                              <span>Gaps</span>
                            </button>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                navigate(`/courses/${course.id}/study-plan`);
                              }}
                              className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 transition-colors"
                              title="View Adaptive Study Plan"
                            >
                              <Calendar className="w-3 h-3 text-purple-600" />
                              <span>Plan</span>
                            </button>
                          </div>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>

              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col">
                <div className="px-6 py-4 border-b border-gray-100">
                  <h2 className="text-base font-semibold text-gray-900">Upcoming Exams</h2>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Ordered by nearest target date
                  </p>
                </div>

                {upcomingExams.length === 0 ? (
                  <div className="p-6 text-center my-auto">
                    <Calendar className="w-8 h-8 text-gray-300 mx-auto" />
                    <p className="mt-2.5 text-sm font-medium text-gray-700">
                      No upcoming exams scheduled
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      Add an exam date to any course to track countdowns here.
                    </p>
                  </div>
                ) : (
                  <ul className="divide-y divide-gray-100">
                    {upcomingExams.slice(0, 5).map((course) => (
                      <li key={course.id}>
                        <Link
                          to={`/courses/${course.id}`}
                          className="block px-6 py-3.5 hover:bg-gray-50 transition-colors"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-medium text-gray-900 truncate">
                              {course.title}
                            </span>
                            <span
                              className={`text-xs font-semibold flex-shrink-0 ${
                                course.exam_status === 'today' ||
                                course.exam_status === 'urgent'
                                  ? 'text-orange-700'
                                  : 'text-indigo-600'
                              }`}
                            >
                              {getExamCountdownText(course)}
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-gray-500">
                            {formatCalendarDate(course.exam_date)} &bull;{' '}
                            {formatStudyMinutes(course.daily_minutes)}/day
                          </p>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>
          )}
        </>
      )}

      <CourseFormModal
        isOpen={isCreateModalOpen}
        mode="create"
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateCourse}
      />
    </div>
  );
};

export default Dashboard;

