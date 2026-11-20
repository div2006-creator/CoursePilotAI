import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  Clock,
  HelpCircle,
  Network,
  RotateCcw,
  Sparkles,
  TrendingDown,
  TrendingUp,
  X,
  XCircle,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { getDiagnosticResult } from '../services/diagnosticService';
import { getCourseById } from '../services/courseService';
import { Course, DiagnosticResultData } from '../types';
import { extractApiErrorMessage } from '../services/api';

export const DiagnosticResult: React.FC = () => {
  const { courseId, sessionId } = useParams<{ courseId: string; sessionId: string }>();

  const [course, setCourse] = useState<Course | null>(null);
  const [result, setResult] = useState<DiagnosticResultData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    const loadData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [resultData, courseData] = await Promise.all([
          getDiagnosticResult(sessionId),
          courseId ? getCourseById(courseId) : Promise.resolve(null),
        ]);
        setResult(resultData);
        if (courseData?.data) setCourse(courseData.data);
      } catch (err) {
        setError(extractApiErrorMessage(err, 'Failed to load diagnostic results.'));
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [courseId, sessionId]);

  const formatDuration = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    if (mins === 0) return `${secs}s`;
    return `${mins}m ${secs}s`;
  };

  const getPerformanceBadge = (score: number) => {
    if (score >= 75) {
      return {
        label: 'Strong Foundation',
        color: 'text-emerald-700 bg-emerald-100 border-emerald-300',
        summary: 'Excellent conceptual grasp across assessed topics.',
      };
    }
    if (score >= 50) {
      return {
        label: 'Moderate Knowledge',
        color: 'text-amber-700 bg-amber-100 border-amber-300',
        summary: 'Good baseline, but key topics require structured revision.',
      };
    }
    return {
      label: 'Needs Priority Attention',
      color: 'text-rose-700 bg-rose-100 border-rose-300',
      summary: 'Significant gaps detected. Prioritize foundational prerequisites.',
    };
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <h2 className="text-xl font-bold text-slate-800">Calculating Diagnostic Analytics...</h2>
        <p className="text-sm text-slate-500 mt-1">Evaluating topic accuracy and knowledge profile</p>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <div className="w-16 h-16 bg-rose-100 text-rose-700 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <HelpCircle className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">Results Unavailable</h2>
        <p className="text-slate-600 text-sm max-w-md mx-auto mb-6">
          {error || 'Unable to find results for this diagnostic assessment session.'}
        </p>
        <Link
          to={`/courses/${courseId || ''}`}
          className="inline-flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          <span>Return to Course</span>
        </Link>
      </div>
    );
  }

  const perf = getPerformanceBadge(result.score);

  // Prepare chart data for topic accuracy
  const chartData = result.topic_accuracies
    .filter((t) => t.total_questions > 0)
    .map((t) => ({
      name: t.topic_name.length > 20 ? `${t.topic_name.slice(0, 18)}...` : t.topic_name,
      fullName: t.topic_name,
      accuracy: t.accuracy_percentage,
      status: t.status,
    }));

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Breadcrumb Navigation */}
      <div className="flex items-center justify-between mb-6">
        <Link
          to={`/courses/${courseId}`}
          className="inline-flex items-center text-sm font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" />
          Back to {course?.title || 'Course Details'}
        </Link>

        <div className="flex items-center space-x-3">
          <Link
            to={`/courses/${courseId}/diagnostic`}
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs sm:text-sm font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Retake Diagnostic</span>
          </Link>

          <Link
            to={`/courses/${courseId}/graph`}
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs sm:text-sm font-medium text-indigo-600 bg-indigo-50 border border-indigo-200 hover:bg-indigo-100 transition-colors"
          >
            <Network className="w-3.5 h-3.5" />
            <span>View Graph</span>
          </Link>
        </div>
      </div>

      {/* Main Score & Performance Banner */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-10 mb-8">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8 pb-8 border-b border-slate-100">
          <div>
            <div className="flex items-center space-x-2">
              <span className="p-1 rounded-md bg-indigo-100 text-indigo-700">
                <Sparkles className="w-4 h-4" />
              </span>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Assessment Results Summary
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-2">
              {course?.title || 'Course'} Diagnostic Result
            </h1>
            <p className="text-slate-600 text-sm mt-1 max-w-xl">{perf.summary}</p>
          </div>

          {/* Score Badge */}
          <div className="flex items-center space-x-6">
            <div className="flex flex-col items-center justify-center w-32 h-32 rounded-3xl bg-slate-900 text-white shadow-xl p-4">
              <span className="text-3xl font-extrabold tracking-tight">
                {Math.round(result.score)}%
              </span>
              <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold mt-1">
                Accuracy
              </span>
            </div>

            <div className="space-y-2">
              <span
                className={`inline-block px-3 py-1 rounded-full text-xs font-bold border ${perf.color}`}
              >
                {perf.label}
              </span>
              <div className="text-xs text-slate-500 flex items-center space-x-1.5">
                <Clock className="w-3.5 h-3.5" />
                <span>Time: {formatDuration(result.duration_seconds)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Stat Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-6">
          <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Total Questions
            </span>
            <p className="text-2xl font-bold text-slate-900 mt-1">{result.total_questions}</p>
          </div>

          <div className="bg-emerald-50/60 rounded-2xl p-4 border border-emerald-200">
            <span className="text-xs font-semibold text-emerald-800 uppercase tracking-wider flex items-center space-x-1">
              <Check className="w-3.5 h-3.5 text-emerald-600" />
              <span>Correct Answers</span>
            </span>
            <p className="text-2xl font-bold text-emerald-700 mt-1">{result.correct_answers}</p>
          </div>

          <div className="bg-rose-50/60 rounded-2xl p-4 border border-rose-200">
            <span className="text-xs font-semibold text-rose-800 uppercase tracking-wider flex items-center space-x-1">
              <X className="w-3.5 h-3.5 text-rose-600" />
              <span>Incorrect Answers</span>
            </span>
            <p className="text-2xl font-bold text-rose-700 mt-1">{result.incorrect_answers}</p>
          </div>

          <div className="bg-indigo-50/60 rounded-2xl p-4 border border-indigo-200">
            <span className="text-xs font-semibold text-indigo-800 uppercase tracking-wider">
              Strong Topics
            </span>
            <p className="text-2xl font-bold text-indigo-700 mt-1">
              {result.strongest_topics.length}
            </p>
          </div>
        </div>
      </div>

      {/* Strengths & Weak Areas Callouts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Identified Strengths */}
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-center space-x-2.5 mb-4 pb-3 border-b border-slate-100">
            <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">Identified Strengths</h3>
              <p className="text-xs text-slate-500">Mastery $\ge 75\%$ accuracy</p>
            </div>
          </div>

          {result.strongest_topics.length > 0 ? (
            <div className="space-y-2">
              {result.strongest_topics.map((tName, idx) => (
                <div
                  key={idx}
                  className="flex items-center space-x-2 p-2.5 rounded-xl bg-emerald-50/50 border border-emerald-200 text-emerald-900 text-sm font-medium"
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>{tName}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500 italic p-3 bg-slate-50 rounded-xl">
              No topics reached 75% accuracy yet. Structured practice recommended.
            </p>
          )}
        </div>

        {/* Priority Revision Topics */}
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-center space-x-2.5 mb-4 pb-3 border-b border-slate-100">
            <div className="w-8 h-8 rounded-xl bg-rose-100 text-rose-700 flex items-center justify-center">
              <TrendingDown className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">Priority Revision Topics</h3>
              <p className="text-xs text-slate-500">Mastery &lt; 50% accuracy</p>
            </div>
          </div>

          {result.weak_topics.length > 0 ? (
            <div className="space-y-2">
              {result.weak_topics.map((tName, idx) => (
                <div
                  key={idx}
                  className="flex items-center space-x-2 p-2.5 rounded-xl bg-rose-50/50 border border-rose-200 text-rose-900 text-sm font-medium"
                >
                  <XCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                  <span>{tName}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-emerald-700 italic p-3 bg-emerald-50 rounded-xl">
              Great work! No weak topics below 50% threshold detected.
            </p>
          )}
        </div>
      </div>

      {/* Topic-Wise Accuracy Chart */}
      {chartData.length > 0 && (
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8 mb-8">
          <h3 className="text-lg font-bold text-slate-900 mb-2">Topic Accuracy Breakdown</h3>
          <p className="text-xs text-slate-500 mb-6">
            Percentage accuracy per topic evaluated during this diagnostic run
          </p>

          <div className="h-64 sm:h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 40 }}>
                <XAxis
                  dataKey="name"
                  interval={0}
                  angle={-25}
                  textAnchor="end"
                  tick={{ fontSize: 11, fill: '#475569' }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 11, fill: '#475569' }}
                  tickFormatter={(val) => `${val}%`}
                />
                <Tooltip
                  formatter={(value: any) => [`${value}%`, 'Accuracy']}
                  labelFormatter={(name, payload) => {
                    const item = payload?.[0]?.payload;
                    return item ? item.fullName : name;
                  }}
                />
                <Bar dataKey="accuracy" radius={[6, 6, 0, 0]}>
                  {chartData.map((entry, index) => {
                    let fillColor = '#e11d48'; // weak red
                    if (entry.accuracy >= 75) fillColor = '#059669'; // strong emerald
                    else if (entry.accuracy >= 50) fillColor = '#d97706'; // moderate amber
                    return <Cell key={`cell-${index}`} fill={fillColor} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Difficulty Level Breakdown */}
      {result.difficulty_breakdown.length > 0 && (
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8 mb-8">
          <h3 className="text-lg font-bold text-slate-900 mb-4">Performance by Question Difficulty</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {result.difficulty_breakdown.map((diff, idx) => (
              <div key={idx} className="p-4 rounded-2xl bg-slate-50 border border-slate-200">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    {diff.difficulty}
                  </span>
                  <span className="text-sm font-extrabold text-slate-900">
                    {Math.round(diff.accuracy_percentage)}%
                  </span>
                </div>
                <div className="text-xs text-slate-500">
                  {diff.correct} of {diff.total} correct
                </div>
                <div className="w-full h-2 bg-slate-200 rounded-full mt-2 overflow-hidden">
                  <div
                    className="h-full bg-indigo-600 rounded-full"
                    style={{ width: `${diff.accuracy_percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detailed Question Review List */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8">
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-100">
          <div>
            <h3 className="text-lg sm:text-xl font-bold text-slate-900">
              Question-by-Question Review
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Review your answers, correct solutions, and conceptual explanations
            </p>
          </div>
          <span className="text-xs font-semibold px-3 py-1 rounded-full bg-slate-100 text-slate-700">
            {result.questions_review.length} Questions
          </span>
        </div>

        <div className="space-y-6">
          {result.questions_review.map((item, idx) => {
            const isCorrect = item.is_correct;

            return (
              <div
                key={item.question_id}
                className={`p-6 rounded-2xl border-2 transition-all ${
                  isCorrect
                    ? 'border-emerald-200 bg-emerald-50/20'
                    : 'border-rose-200 bg-rose-50/20'
                }`}
              >
                {/* Header */}
                <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-700">
                      Q{idx + 1}
                    </span>
                    <span className="text-xs font-medium text-slate-600">
                      {item.topic_name}
                    </span>
                  </div>

                  <span
                    className={`inline-flex items-center space-x-1 text-xs font-bold px-2.5 py-0.5 rounded-full ${
                      isCorrect
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        : 'bg-rose-100 text-rose-800 border border-rose-300'
                    }`}
                  >
                    {isCorrect ? (
                      <>
                        <Check className="w-3.5 h-3.5" />
                        <span>Correct</span>
                      </>
                    ) : (
                      <>
                        <X className="w-3.5 h-3.5" />
                        <span>Incorrect</span>
                      </>
                    )}
                  </span>
                </div>

                {/* Prompt */}
                <h4 className="text-base font-semibold text-slate-900 mb-4">{item.question}</h4>

                {/* Options List */}
                <div className="space-y-2 mb-4">
                  {item.options.map((opt, optIdx) => {
                    const isSelected = item.selected_answer === opt;
                    const isCorrectAnswer = item.correct_answer === opt;

                    let optStyle = 'border-slate-200 bg-white text-slate-700';
                    if (isCorrectAnswer) {
                      optStyle = 'border-emerald-400 bg-emerald-50 text-emerald-900 font-semibold';
                    } else if (isSelected && !isCorrect) {
                      optStyle = 'border-rose-300 bg-rose-50 text-rose-900 font-medium line-through';
                    }

                    return (
                      <div
                        key={optIdx}
                        className={`flex items-center justify-between p-3 rounded-xl border text-sm ${optStyle}`}
                      >
                        <div className="flex items-center space-x-2.5">
                          <span className="w-6 h-6 rounded-md bg-slate-100 text-slate-600 flex items-center justify-center font-bold text-xs">
                            {['A', 'B', 'C', 'D'][optIdx] || `${optIdx + 1}`}
                          </span>
                          <span>{opt}</span>
                        </div>

                        {isCorrectAnswer && (
                          <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-100">
                            Correct Answer
                          </span>
                        )}
                        {isSelected && !isCorrectAnswer && (
                          <span className="text-xs font-medium text-rose-700 px-2 py-0.5 rounded bg-rose-100">
                            Your Choice
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Explanation */}
                {item.explanation && (
                  <div className="p-3.5 rounded-xl bg-slate-100 border border-slate-200 text-xs text-slate-700 leading-relaxed">
                    <span className="font-bold text-slate-900 mr-1.5">Explanation:</span>
                    {item.explanation}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
