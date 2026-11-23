import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BookOpen,
  CheckCircle,
  Clock,
  Dumbbell,
  HelpCircle,
  Play,
  RotateCcw,
  SkipForward,
  AlertTriangle,
  Loader2,
  Bot,
} from 'lucide-react';
import { PlanItem, PlanItemStatus } from '../../types';

interface StudySessionCardProps {
  session: PlanItem;
  courseId?: string;
  onUpdateStatus: (sessionId: string, newStatus: PlanItemStatus) => Promise<void>;
}

export const StudySessionCard: React.FC<StudySessionCardProps> = ({
  session,
  courseId,
  onUpdateStatus,
}) => {
  const [isUpdating, setIsUpdating] = useState(false);

  const handleStatusChange = async (status: PlanItemStatus) => {
    try {
      setIsUpdating(true);
      await onUpdateStatus(session.id, status);
    } finally {
      setIsUpdating(false);
    }
  };

  const getSessionTypeBadge = () => {
    switch (session.session_type.toUpperCase()) {
      case 'LEARN':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <BookOpen className="w-3 h-3" />
            <span>Learn</span>
          </span>
        );
      case 'PRACTICE':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <Dumbbell className="w-3 h-3" />
            <span>Practice</span>
          </span>
        );
      case 'REVISION':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <RotateCcw className="w-3 h-3" />
            <span>Revision</span>
          </span>
        );
      case 'ASSESSMENT':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            <HelpCircle className="w-3 h-3" />
            <span>Diagnostic</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-50 text-gray-700 border border-gray-200">
            <span>{session.session_type}</span>
          </span>
        );
    }
  };

  const getDifficultyBadge = () => {
    const diff = (session.difficulty || 'medium').toLowerCase();
    switch (diff) {
      case 'easy':
      case 'beginner':
        return (
          <span className="text-xs px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 font-medium">
            Easy
          </span>
        );
      case 'hard':
      case 'advanced':
        return (
          <span className="text-xs px-2 py-0.5 rounded-md bg-red-50 text-red-700 font-medium">
            Hard
          </span>
        );
      default:
        return (
          <span className="text-xs px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 font-medium">
            Medium
          </span>
        );
    }
  };

  const isCompleted = session.status === 'COMPLETED';
  const isInProgress = session.status === 'IN_PROGRESS';
  const isSkipped = session.status === 'SKIPPED';

  return (
    <div
      className={`relative rounded-xl border p-4 transition-all duration-200 ${
        isCompleted
          ? 'bg-emerald-50/30 border-emerald-200 shadow-2xs'
          : isInProgress
          ? 'bg-indigo-50/40 border-indigo-300 shadow-xs ring-1 ring-indigo-200'
          : isSkipped
          ? 'bg-gray-50/70 border-gray-200 opacity-60'
          : 'bg-white border-gray-200 hover:border-gray-300 shadow-xs'
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        {/* Left: Topic Title & Meta */}
        <div className="space-y-1.5 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {getSessionTypeBadge()}
            {getDifficultyBadge()}
            <span className="text-xs text-gray-400 font-mono">
              Priority: {Math.round(session.priority_score)}%
            </span>
          </div>

          <h4
            className={`text-base font-semibold ${
              isCompleted ? 'text-gray-600 line-through' : 'text-gray-900'
            }`}
          >
            {session.topic_name}
          </h4>

          {session.unit_name && (
            <p className="text-xs text-gray-500 font-medium">{session.unit_name}</p>
          )}

          {/* Prerequisite Blocker Alert */}
          {!session.is_prerequisite_satisfied && session.unmet_prerequisites.length > 0 && (
            <div className="mt-2 inline-flex items-center space-x-1.5 text-xs text-amber-800 bg-amber-50 px-2.5 py-1 rounded-md border border-amber-200">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
              <span>
                Foundational prerequisites pending: {session.unmet_prerequisites.join(', ')}
              </span>
            </div>
          )}
        </div>

        {/* Right: Duration & Actions */}
        <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-3 flex-shrink-0">
          <div className="inline-flex items-center space-x-1 text-xs font-semibold text-gray-700 bg-gray-100 px-2.5 py-1 rounded-md">
            <Clock className="w-3.5 h-3.5 text-gray-500" />
            <span>{session.duration_minutes} min</span>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center space-x-1.5">
            <Link
              to={
                courseId
                  ? `/courses/${courseId}/topics/${session.topic_id}/tutor?plan_item_id=${session.id}`
                  : `/tutor?topic_id=${session.topic_id}&plan_item_id=${session.id}`
              }
              className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors shadow-2xs"
              title="Launch AI Tutor for this topic"
            >
              <Bot className="w-3.5 h-3.5" />
              <span>Tutor</span>
            </Link>

            {isUpdating ? (
              <Loader2 className="w-4 h-4 text-indigo-600 animate-spin" />
            ) : isCompleted ? (
              <button
                type="button"
                onClick={() => handleStatusChange('PENDING')}
                title="Mark uncompleted"
                className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-medium text-emerald-800 bg-emerald-100 hover:bg-emerald-200 transition-colors"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                <span>Done</span>
              </button>
            ) : isInProgress ? (
              <>
                <button
                  type="button"
                  onClick={() => handleStatusChange('COMPLETED')}
                  className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition-colors shadow-xs"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  <span>Complete</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleStatusChange('SKIPPED')}
                  className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors"
                  title="Skip session"
                >
                  <SkipForward className="w-3.5 h-3.5" />
                </button>
              </>
            ) : isSkipped ? (
              <button
                type="button"
                onClick={() => handleStatusChange('PENDING')}
                className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-medium text-gray-600 bg-gray-200 hover:bg-gray-300 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Restore</span>
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => handleStatusChange('IN_PROGRESS')}
                  className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors"
                >
                  <Play className="w-3 h-3 fill-current" />
                  <span>Start</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleStatusChange('COMPLETED')}
                  className="inline-flex items-center space-x-1 px-2 py-1 rounded-md text-xs font-medium text-gray-600 hover:text-emerald-700 hover:bg-emerald-50 transition-colors"
                  title="Quick complete"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

