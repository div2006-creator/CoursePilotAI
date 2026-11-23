import React from 'react';
import {
  Calendar,
  CheckCircle2,
  Clock,
  AlertTriangle,
  TrendingUp,
  AlertCircle,
} from 'lucide-react';
import { StudyPlanProgress } from '../../types';

interface PlanProgressProps {
  progress: StudyPlanProgress;
}

export const PlanProgress: React.FC<PlanProgressProps> = ({ progress }) => {
  const formatTime = (minutes: number) => {
    const hrs = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hrs === 0) return `${mins}m`;
    if (mins === 0) return `${hrs}h`;
    return `${hrs}h ${mins}m`;
  };

  return (
    <div className="space-y-4">
      {/* Insufficient Time / Unslotted Topics Warning */}
      {progress.unslotted_topics_count > 0 && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 flex items-start space-x-3 text-amber-900 shadow-xs">
          <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1 text-sm">
            <span className="font-semibold">
              Time Horizon Warning: {progress.unslotted_topics_count} topic(s) cannot fit before the exam date!
            </span>
            <p className="mt-1 text-amber-800 text-xs leading-relaxed">
              Based on your {progress.daily_minutes_target} min/day limit and exam date, the following topics were excluded from the schedule:{' '}
              <span className="font-medium text-amber-950">
                {progress.unslotted_topic_names.join(', ')}
              </span>
              . Consider increasing your daily study time or rescheduling the exam to cover all topics.
            </p>
          </div>
        </div>
      )}

      {/* Progress Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Completion % */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs font-medium text-gray-500">
            <span>Overall Completion</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-gray-900">
              {progress.completion_percentage}%
            </span>
            <span className="text-xs text-gray-500">
              ({progress.completed_items}/{progress.total_items} sessions)
            </span>
          </div>
          <div className="mt-2.5 w-full bg-gray-100 rounded-full h-2 overflow-hidden">
            <div
              className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, progress.completion_percentage)}%` }}
            />
          </div>
        </div>

        {/* Study Time */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs font-medium text-gray-500">
            <span>Study Time</span>
            <Clock className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-gray-900">
              {formatTime(progress.completed_minutes)}
            </span>
            <span className="text-xs text-gray-500">
              / {formatTime(progress.total_minutes_scheduled)}
            </span>
          </div>
          <div className="mt-2.5 flex items-center text-xs text-gray-500">
            <span>Target: {progress.daily_minutes_target}m / day</span>
          </div>
        </div>

        {/* Exam Countdown */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs font-medium text-gray-500">
            <span>Exam Horizon</span>
            <Calendar className="w-4 h-4 text-purple-600" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-gray-900">
              {progress.days_remaining !== null ? (
                progress.days_remaining === 0 ? (
                  'Today!'
                ) : (
                  `${progress.days_remaining}d`
                )
              ) : (
                'Rolling'
              )}
            </span>
            {progress.days_remaining !== null && (
              <span className="text-xs text-gray-500">remaining</span>
            )}
          </div>
          <div className="mt-2.5 text-xs text-gray-500 truncate">
            {progress.target_exam_date
              ? `Target: ${progress.target_exam_date}`
              : 'Rolling 7-day schedule'}
          </div>
        </div>

        {/* Pace & Schedule Health */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs font-medium text-gray-500">
            <span>Schedule Health</span>
            {progress.is_on_track ? (
              <TrendingUp className="w-4 h-4 text-emerald-600" />
            ) : (
              <AlertCircle className="w-4 h-4 text-amber-600" />
            )}
          </div>
          <div className="mt-2 flex items-center space-x-2">
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                progress.is_on_track
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-amber-100 text-amber-800'
              }`}
            >
              {progress.is_on_track ? 'On Track' : 'Needs Attention'}
            </span>
          </div>
          <div className="mt-2.5 text-xs text-gray-500">
            {progress.in_progress_items > 0 ? (
              <span>{progress.in_progress_items} in progress</span>
            ) : progress.skipped_items > 0 ? (
              <span>{progress.skipped_items} session(s) skipped</span>
            ) : (
              <span>All current sessions paced</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
