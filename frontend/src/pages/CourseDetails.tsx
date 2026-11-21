import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Award,
  BookOpen,
  BrainCircuit,
  Calendar,
  CheckCircle2,
  Clock,
  FileText,
  GitFork,
  History,
  Layers,
  Loader2,
  Pencil,
  RefreshCw,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react';
import {
  Course,
  CourseCreatePayload,
  CourseTopicsData,
  CourseUpdatePayload,
  DiagnosticHistoryItem,
} from '../types';
import { courseService } from '../services/courseService';
import { topicService } from '../services/topicService';
import { getDiagnosticHistory } from '../services/diagnosticService';
import { extractApiErrorMessage } from '../services/api';
import {
  formatCalendarDate,
  formatStudyMinutes,
  formatTimestampDate,
  getCourseStatusMeta,
  getExamCountdownText,
} from '../utils/courseFormatters';
import { CourseFormModal, DeleteCourseModal } from '../components/course';

export const CourseDetails: React.FC = () => {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();

  const [course, setCourse] = useState<Course | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);

  // Topics extraction state
  const [topicsData, setTopicsData] = useState<CourseTopicsData | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);

  // Diagnostic history state
  const [diagnosticHistory, setDiagnosticHistory] = useState<DiagnosticHistoryItem[]>([]);

  const fetchCourse = useCallback(async () => {
    if (!courseId) {
      setNotFound(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setNotFound(false);
    setLoadError(null);
    try {
      const response = await courseService.getCourseById(courseId);
      setCourse(response.data);

      // Load topics for this course
      try {
        const topicsRes = await topicService.getCourseTopics(courseId);
        setTopicsData(topicsRes.data);
      } catch {
        setTopicsData(null);
      }

      // Load diagnostic assessment history
      try {
        const historyRes = await getDiagnosticHistory(courseId);
        setDiagnosticHistory(historyRes);
      } catch {
        setDiagnosticHistory([]);
      }
    } catch (error) {
      if (
        axios.isAxiosError(error) &&
        (error.response?.status === 404 || error.response?.status === 422)
      ) {
        setNotFound(true);
      } else {
        setLoadError(
          extractApiErrorMessage(error, 'Failed to load course details. Please try again.')
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, [courseId]);

  const handleExtractTopics = async () => {
    if (!courseId) return;
    setIsExtracting(true);
    setExtractError(null);
    try {
      const res = await topicService.extractTopics(courseId);
      setNotice(
        `AI successfully extracted ${res.data.topics_created} topics and ${res.data.prerequisites_created} prerequisite edges!`
      );
      const topicsRes = await topicService.getCourseTopics(courseId);
      setTopicsData(topicsRes.data);
    } catch (err) {
      setExtractError(
        extractApiErrorMessage(err, 'Topic extraction failed. Please ensure syllabus documents are uploaded.')
      );
    } finally {
      setIsExtracting(false);
    }
  };

  useEffect(() => {
    void fetchCourse();
  }, [fetchCourse]);

  const handleUpdateCourse = async (
    payload: CourseCreatePayload | CourseUpdatePayload
  ) => {
    if (!course) {
      return;
    }
    const response = await courseService.updateCourse(
      course.id,
      payload as CourseUpdatePayload
    );
    setCourse(response.data);
    setIsEditOpen(false);
    setNotice('Course details updated successfully.');
  };

  const handleDeleteCourse = async (target: Course) => {
    await courseService.deleteCourse(target.id);
    navigate('/courses', {
      replace: true,
      state: { notice: `Course "${target.title}" was deleted.` },
    });
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-12 flex flex-col items-center justify-center text-center">
        <Loader2 className="w-7 h-7 text-indigo-600 animate-spin" />
        <p className="mt-3 text-sm font-medium text-gray-700">Loading course details...</p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-10 text-center max-w-xl mx-auto">
        <div className="mx-auto w-12 h-12 rounded-xl bg-gray-100 text-gray-500 flex items-center justify-center">
          <BookOpen className="w-6 h-6" />
        </div>
        <h1 className="mt-4 text-xl font-bold text-gray-900">Course Not Found</h1>
        <p className="mt-2 text-sm text-gray-500">
          This course does not exist or you do not have permission to view it.
        </p>
        <Link
          to="/courses"
          className="mt-5 inline-flex items-center space-x-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Courses</span>
        </Link>
      </div>
    );
  }

  if (loadError || !course) {
    return (
      <div className="bg-white rounded-xl border border-red-200 p-8 text-center max-w-xl mx-auto">
        <div className="mx-auto w-11 h-11 rounded-full bg-red-50 text-red-600 flex items-center justify-center">
          <AlertCircle className="w-5 h-5" />
        </div>
        <h1 className="mt-3 text-base font-semibold text-gray-900">
          Unable to load course
        </h1>
        <p className="mt-1 text-sm text-gray-500">{loadError}</p>
        <div className="mt-4 flex items-center justify-center space-x-3">
          <Link
            to="/courses"
            className="inline-flex items-center space-x-1.5 rounded-lg border border-gray-300 bg-white px-3.5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Courses</span>
          </Link>
          <button
            type="button"
            onClick={() => void fetchCourse()}
            className="inline-flex items-center space-x-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Try Again</span>
          </button>
        </div>
      </div>
    );
  }

  const statusMeta = getCourseStatusMeta(course);
  const countdownText = getExamCountdownText(course);
  const weeklyMinutes = course.daily_minutes * 7;

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/courses"
          className="inline-flex items-center space-x-1.5 text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to My Courses</span>
        </Link>
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

      {extractError && (
        <div
          role="alert"
          className="flex items-start space-x-2.5 rounded-lg border border-red-200 bg-red-50 p-3.5 text-sm text-red-700"
        >
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <span className="font-semibold">Extraction notice: </span>
            <span>{extractError}</span>
          </div>
          <button
            type="button"
            onClick={() => setExtractError(null)}
            className="p-1 rounded text-red-700 hover:bg-red-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <section className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div className="space-y-2.5 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
                {course.title}
              </h1>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusMeta.badgeClassName}`}
              >
                {statusMeta.label}
              </span>
            </div>
            <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-line">
              {course.description ? (
                course.description
              ) : (
                <span className="text-gray-400 italic">
                  No course description provided. Click Edit Course to add syllabus notes or learning goals.
                </span>
              )}
            </p>
          </div>

          <div className="flex items-center space-x-2.5 flex-shrink-0">
            <button
              type="button"
              onClick={() => setIsEditOpen(true)}
              className="inline-flex items-center space-x-1.5 rounded-lg border border-gray-300 bg-white px-3.5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <Pencil className="w-4 h-4" />
              <span>Edit Course</span>
            </button>
            <button
              type="button"
              onClick={() => setIsDeleteOpen(true)}
              className="inline-flex items-center space-x-1.5 rounded-lg border border-red-200 bg-red-50 px-3.5 py-2 text-sm font-medium text-red-700 hover:bg-red-100 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              <span>Delete</span>
            </button>
          </div>
        </div>

        {course.is_exam_passed && (
          <div className="mt-5 flex items-start space-x-2.5 rounded-lg border border-amber-200 bg-amber-50 p-3.5 text-sm text-amber-800">
            <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-600" />
            <span>
              The exam date ({formatCalendarDate(course.exam_date)}) has already passed. You can
              keep this course for review or update the exam date if you are preparing for a retake.
            </span>
          </div>
        )}
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
              Exam Countdown
            </span>
            <Calendar className="w-4 h-4 text-indigo-600" />
          </div>
          <p className="mt-2.5 text-xl font-bold text-gray-900">{countdownText}</p>
          <p className="mt-1 text-xs text-gray-500">
            Target date: {formatCalendarDate(course.exam_date)}
          </p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
              Daily Study Availability
            </span>
            <Clock className="w-4 h-4 text-indigo-600" />
          </div>
          <p className="mt-2.5 text-xl font-bold text-gray-900">
            {formatStudyMinutes(course.daily_minutes)} / day
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {course.daily_minutes} min daily &bull; ~{formatStudyMinutes(weeklyMinutes)} per week
          </p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
              Created On
            </span>
            <BookOpen className="w-4 h-4 text-indigo-600" />
          </div>
          <p className="mt-2.5 text-xl font-bold text-gray-900">
            {formatTimestampDate(course.created_at)}
          </p>
          <p className="mt-1 text-xs text-gray-500">Status: {statusMeta.label}</p>
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <FileText className="w-5 h-5" />
              </div>
              <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-600">
                Coming Soon
              </span>
            </div>
            <h2 className="mt-4 text-base font-semibold text-gray-900">Documents</h2>
            <p className="mt-1.5 text-sm text-gray-500 leading-relaxed">
              Upload course syllabi, lecture notes, and textbooks here in an upcoming update to
              power document indexing and study recommendations.
            </p>
          </div>
          <p className="mt-4 pt-3 border-t border-gray-100 text-xs text-gray-400">
            0 documents uploaded
          </p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <Layers className="w-5 h-5" />
              </div>
              <span
                className={`text-xs font-medium px-2.5 py-0.5 rounded-full border ${
                  topicsData && topicsData.total_topics > 0
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : 'bg-amber-50 text-amber-700 border-amber-200'
                }`}
              >
                {topicsData && topicsData.total_topics > 0 ? 'AI Extracted' : 'Not Extracted'}
              </span>
            </div>

            <h2 className="mt-4 text-base font-semibold text-gray-900">
              Topics & Knowledge Graph
            </h2>
            <p className="mt-1.5 text-sm text-gray-500 leading-relaxed">
              {topicsData && topicsData.total_topics > 0
                ? `${topicsData.total_units} units, ${topicsData.total_topics} topics, and ${topicsData.total_subtopics} subtopics organized into a directed prerequisite graph.`
                : 'Extract syllabus topics, concepts, and foundational prerequisite dependencies using local AI.'}
            </p>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
            {topicsData && topicsData.total_topics > 0 ? (
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  to={`/courses/${course.id}/topics`}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 transition-colors"
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>View Topics ({topicsData.total_topics})</span>
                </Link>
                <Link
                  to={`/courses/${course.id}/graph`}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 transition-colors shadow-sm"
                >
                  <GitFork className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Knowledge Graph</span>
                </Link>
                <button
                  type="button"
                  onClick={handleExtractTopics}
                  disabled={isExtracting}
                  title="Re-extract syllabus topics"
                  className="p-1.5 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-gray-100 disabled:opacity-50 transition-colors"
                >
                  {isExtracting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={handleExtractTopics}
                disabled={isExtracting}
                className="w-full inline-flex items-center justify-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-60 transition-colors"
              >
                {isExtracting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                )}
                <span>{isExtracting ? 'Extracting with AI...' : 'Extract Topics with AI'}</span>
              </button>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <Award className="w-5 h-5" />
              </div>
              {diagnosticHistory.length > 0 && diagnosticHistory[0].status === 'completed' ? (
                <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                  {Math.round(diagnosticHistory[0].score)}% Latest Score
                </span>
              ) : (
                <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-600">
                  Diagnostic Ready
                </span>
              )}
            </div>
            <h2 className="mt-4 text-base font-semibold text-gray-900">
              Diagnostic Assessment
            </h2>
            <p className="mt-1.5 text-sm text-gray-500 leading-relaxed">
              {diagnosticHistory.length > 0 && diagnosticHistory[0].status === 'completed'
                ? `Completed ${diagnosticHistory.length} diagnostic session(s). Evaluates baseline topic strengths and knowledge gaps.`
                : 'Take an adaptive diagnostic test to identify your strengths and pinpoint topics that need revision.'}
            </p>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-100 space-y-2">
            <div className="flex items-center space-x-2">
              <Link
                to={`/courses/${course.id}/diagnostic`}
                className="flex-1 inline-flex items-center justify-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-sm"
              >
                <Award className="w-3.5 h-3.5" />
                <span>{diagnosticHistory.length > 0 ? 'Retake Diagnostic' : 'Start Diagnostic'}</span>
              </Link>
              {diagnosticHistory.length > 0 && diagnosticHistory[0].status === 'completed' && (
                <Link
                  to={`/courses/${course.id}/diagnostic/${diagnosticHistory[0].session_id}/result`}
                  className="inline-flex items-center space-x-1 px-3 py-2 rounded-lg text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
                >
                  <History className="w-3.5 h-3.5" />
                  <span>Latest Result</span>
                </Link>
              )}
            </div>

            <Link
              to={`/courses/${course.id}/knowledge-gaps`}
              className="w-full inline-flex items-center justify-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors shadow-2xs"
            >
              <BrainCircuit className="w-3.5 h-3.5 text-indigo-600" />
              <span>Knowledge Gap Analysis & Prerequisites</span>
            </Link>
          </div>
        </div>
      </section>

      <CourseFormModal
        isOpen={isEditOpen}
        mode="edit"
        initialCourse={course}
        onClose={() => setIsEditOpen(false)}
        onSubmit={handleUpdateCourse}
      />

      <DeleteCourseModal
        course={isDeleteOpen ? course : null}
        onClose={() => setIsDeleteOpen(false)}
        onConfirm={handleDeleteCourse}
      />
    </div>
  );
};

export default CourseDetails;

