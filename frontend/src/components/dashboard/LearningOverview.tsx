import React from 'react';
import {
  CheckCircle2,
  TrendingUp,
  Calendar,
  Clock,
  Layers,
} from 'lucide-react';
import { CourseOverviewData } from '../../types';

interface LearningOverviewProps {
  overview: CourseOverviewData;
  courseTitle?: string;
}

export const LearningOverview: React.FC<LearningOverviewProps> = ({ overview, courseTitle }) => {
  const coveragePct =
    overview.total_topics > 0
      ? Math.round((overview.assessed_topics / overview.total_topics) * 100)
      : 0;

  return (
    <div className="space-y-4">
      {courseTitle && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-gray-100">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{courseTitle}</h2>
            <p className="text-sm text-gray-500">Learning analytics and verified progress intelligence</p>
          </div>
          {overview.exam_date && (
            <div className="mt-2 sm:mt-0 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
              <Calendar className="w-3.5 h-3.5" />
              <span>
                Exam in{' '}
                {overview.days_remaining !== null
                  ? `${overview.days_remaining} day${overview.days_remaining === 1 ? '' : 's'}`
                  : overview.exam_date}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Grid of Key Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Total & Assessed */}
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Assessed Coverage
            </span>
            <Layers className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900">{coveragePct}%</span>
            <span className="text-xs text-gray-500">
              ({overview.assessed_topics}/{overview.total_topics} topics)
            </span>
          </div>
          <div className="mt-2 w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-indigo-600 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${coveragePct}%` }}
            />
          </div>
        </div>

        {/* Average Mastery */}
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Average Mastery
            </span>
            <TrendingUp className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900">
              {overview.average_mastery_percentage !== null
                ? `${overview.average_mastery_percentage}%`
                : '—'}
            </span>
            <span className="text-xs text-gray-500">
              {overview.average_mastery_percentage !== null ? 'verified' : 'unassessed'}
            </span>
          </div>
          <p className="mt-2 text-xs text-gray-400">
            {overview.assessed_topics > 0
              ? `Across ${overview.assessed_topics} assessed topic${overview.assessed_topics === 1 ? '' : 's'}`
              : 'Complete diagnostic to assess'}
          </p>
        </div>

        {/* Study Sessions Completed */}
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Study Sessions
            </span>
            <CheckCircle2 className="w-4 h-4 text-blue-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900">
              {overview.completed_study_sessions}
            </span>
            <span className="text-xs text-gray-500">
              completed ({overview.pending_study_sessions} pending)
            </span>
          </div>
          <p className="mt-2 text-xs text-gray-400">
            {overview.active_plan_version
              ? `Plan v${overview.active_plan_version} active`
              : 'No study plan generated yet'}
          </p>
        </div>

        {/* Practice Attempts */}
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Practice Questions
            </span>
            <Clock className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-gray-900">
              {overview.total_practice_attempts}
            </span>
            <span className="text-xs text-gray-500">attempts</span>
          </div>
          <p className="mt-2 text-xs text-gray-400">
            {overview.total_practice_attempts > 0
              ? 'Tutor and diagnostic sessions'
              : 'No practice logged yet'}
          </p>
        </div>
      </div>
    </div>
  );
};

export default LearningOverview;
