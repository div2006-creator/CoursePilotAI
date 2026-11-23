import React from 'react';
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
} from 'lucide-react';
import { ExamReadinessData } from '../../types';

interface ExamReadinessCardProps {
  data: ExamReadinessData;
}

export const ExamReadinessCard: React.FC<ExamReadinessCardProps> = ({ data }) => {
  const getCategoryTheme = (category: string) => {
    switch (category) {
      case 'Exam Ready':
        return {
          bg: 'bg-emerald-50 text-emerald-800 border-emerald-200',
          meter: 'text-emerald-600 stroke-emerald-500',
          badge: 'bg-emerald-100 text-emerald-800',
        };
      case 'Almost Ready':
        return {
          bg: 'bg-blue-50 text-blue-800 border-blue-200',
          meter: 'text-blue-600 stroke-blue-500',
          badge: 'bg-blue-100 text-blue-800',
        };
      case 'Needs More Practice':
        return {
          bg: 'bg-amber-50 text-amber-800 border-amber-200',
          meter: 'text-amber-600 stroke-amber-500',
          badge: 'bg-amber-100 text-amber-800',
        };
      default:
        return {
          bg: 'bg-rose-50 text-rose-800 border-rose-200',
          meter: 'text-rose-600 stroke-rose-500',
          badge: 'bg-rose-100 text-rose-800',
        };
    }
  };

  const theme = getCategoryTheme(data.category);

  return (
    <div className="bg-white rounded-xl p-5 border border-gray-100 shadow-sm space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-gray-900">Exam Readiness Score</h3>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${theme.badge}`}>
              {data.category}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            Deterministic index calculated from verified topic mastery, graph importance, and recent practice
          </p>
        </div>

        {data.exam_date && (
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium bg-gray-50 border border-gray-200 text-gray-700">
            <Calendar className="w-3.5 h-3.5 text-indigo-600" />
            <span>
              {data.days_remaining !== null
                ? `${data.days_remaining} days until exam (${data.exam_date})`
                : data.exam_date}
            </span>
          </div>
        )}
      </div>

      {/* Coverage / Reliability Warning */}
      {!data.is_reliable && (
        <div className="p-3.5 bg-amber-50/80 border border-amber-200 rounded-lg flex items-start gap-2.5 text-xs text-amber-900">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Preliminary Score &mdash; Low Coverage Warning:</span>{' '}
            {data.coverage_warning ||
              `Only ${data.assessment_coverage_percentage}% of topics have been assessed. At least 40% syllabus coverage is required for reliable readiness confidence.`}
          </div>
        </div>
      )}

      {/* Score and Component Breakdown Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-center">
        {/* Score Dial / Big Number */}
        <div className="md:col-span-4 flex flex-col items-center justify-center p-4 bg-gray-50/60 rounded-xl border border-gray-100 text-center">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            Overall Readiness
          </span>
          <div className="mt-2 text-5xl font-black text-gray-900 tracking-tight">
            {data.readiness_score}
            <span className="text-2xl text-gray-400 font-normal">/100</span>
          </div>
          <span className={`mt-2 px-3 py-1 rounded-full text-xs font-semibold ${theme.bg}`}>
            {data.category}
          </span>
          <span className="mt-2 text-[11px] text-gray-500">
            {data.assessment_coverage_percentage}% assessed ({data.unassessed_topics_count} unassessed)
          </span>
        </div>

        {/* 5 Component Bars */}
        <div className="md:col-span-8 space-y-2.5">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1">
            Component Breakdown (Deterministic Weights)
          </span>

          {/* 1. Topic Mastery (40%) */}
          <div>
            <div className="flex justify-between text-xs font-medium mb-1">
              <span className="text-gray-700">Topic Mastery (40% weight)</span>
              <span className="text-gray-900 font-bold">{data.mastery_component} / 40.0 pts</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
              <div
                className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                style={{ width: `${(data.mastery_component / 40.0) * 100}%` }}
              />
            </div>
          </div>

          {/* 2. Topic Importance (20%) */}
          <div>
            <div className="flex justify-between text-xs font-medium mb-1">
              <span className="text-gray-700">High-Importance Topics (20% weight)</span>
              <span className="text-gray-900 font-bold">{data.importance_component} / 20.0 pts</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                style={{ width: `${(data.importance_component / 20.0) * 100}%` }}
              />
            </div>
          </div>

          {/* 3. Prerequisite Readiness (15%) */}
          <div>
            <div className="flex justify-between text-xs font-medium mb-1">
              <span className="text-gray-700">Prerequisite Health (15% weight)</span>
              <span className="text-gray-900 font-bold">{data.prerequisite_component} / 15.0 pts</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
              <div
                className="bg-emerald-600 h-2 rounded-full transition-all duration-500"
                style={{ width: `${(data.prerequisite_component / 15.0) * 100}%` }}
              />
            </div>
          </div>

          {/* 4. Recent Performance (15%) */}
          <div>
            <div className="flex justify-between text-xs font-medium mb-1">
              <span className="text-gray-700">Recent Form &amp; Practice (15% weight)</span>
              <span className="text-gray-900 font-bold">{data.recent_performance_component} / 15.0 pts</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
              <div
                className="bg-amber-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${(data.recent_performance_component / 15.0) * 100}%` }}
              />
            </div>
          </div>

          {/* 5. Assessment Coverage (10%) */}
          <div>
            <div className="flex justify-between text-xs font-medium mb-1">
              <span className="text-gray-700">Syllabus Coverage (10% weight)</span>
              <span className="text-gray-900 font-bold">{data.coverage_component} / 10.0 pts</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
              <div
                className="bg-teal-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${(data.coverage_component / 10.0) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Recommended Actions checklist */}
      {data.recommended_actions.length > 0 && (
        <div className="p-3.5 bg-gray-50/70 rounded-lg border border-gray-100 space-y-1.5">
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider block">
            Readiness Boosters
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-gray-600">
            {data.recommended_actions.map((act, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                <span>{act}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ExamReadinessCard;
