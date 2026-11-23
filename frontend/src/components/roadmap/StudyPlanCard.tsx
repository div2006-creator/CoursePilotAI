import React from 'react';
import { Link } from 'react-router-dom';
import {
  CheckCircle2,
  Clock,
  Play,
  Lock,
  Layers,
  AlertTriangle,
  ArrowDown,
  Bot,
} from 'lucide-react';
import { PlanItem, PlanItemStatus } from '../../types';

interface StudyPlanCardProps {
  sessions: PlanItem[];
  courseId?: string;
  onUpdateStatus: (sessionId: string, newStatus: PlanItemStatus) => Promise<void>;
}

export const StudyPlanCard: React.FC<StudyPlanCardProps> = ({
  sessions,
  courseId,
  onUpdateStatus,
}) => {
  if (!sessions || sessions.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500">
        <Layers className="w-8 h-8 mx-auto text-gray-300 mb-2" />
        <p className="text-sm">No roadmap topics scheduled yet.</p>
      </div>
    );
  }

  // Sort sessions in sequence order
  const sortedSessions = [...sessions].sort(
    (a, b) => a.sequence_number - b.sequence_number
  );

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xs">
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-gray-100">
        <div>
          <h3 className="text-base font-bold text-gray-900">
            Prerequisite-Guided Learning Roadmap
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Strict topological order: foundational prerequisite concepts must be mastered before dependent topics.
          </p>
        </div>
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700">
          {sessions.length} Steps
        </span>
      </div>

      <div className="relative pl-6 space-y-6">
        {/* Vertical timeline line */}
        <div className="absolute left-3 top-3 bottom-3 w-0.5 bg-gray-200" />

        {sortedSessions.map((item, index) => {
          const isDone = item.status === 'COMPLETED';
          const isInProgress = item.status === 'IN_PROGRESS';
          const isBlocked = !item.is_prerequisite_satisfied;

          return (
            <div key={item.id} className="relative group">
              {/* Timeline marker icon */}
              <div
                className={`absolute -left-6 top-1.5 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all shadow-xs ${
                  isDone
                    ? 'bg-emerald-600 text-white ring-4 ring-emerald-50'
                    : isInProgress
                    ? 'bg-indigo-600 text-white ring-4 ring-indigo-50'
                    : isBlocked
                    ? 'bg-amber-500 text-white ring-4 ring-amber-50'
                    : 'bg-white border-2 border-gray-300 text-gray-600'
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : isBlocked ? (
                  <Lock className="w-3 h-3" />
                ) : (
                  <span>{index + 1}</span>
                )}
              </div>

              {/* Node Card */}
              <div
                className={`rounded-xl border p-4 transition-all ml-3 ${
                  isDone
                    ? 'bg-emerald-50/20 border-emerald-200'
                    : isInProgress
                    ? 'bg-indigo-50/30 border-indigo-300 shadow-xs ring-1 ring-indigo-200'
                    : isBlocked
                    ? 'bg-amber-50/30 border-amber-200'
                    : 'bg-white border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className="text-xs font-bold uppercase tracking-wide text-indigo-600">
                        {item.session_type}
                      </span>
                      <span className="text-gray-300">&bull;</span>
                      <span className="text-xs text-gray-500">
                        Scheduled for: {item.scheduled_date}
                      </span>
                      <span className="text-gray-300">&bull;</span>
                      <span className="text-xs text-gray-500 capitalize">
                        {item.difficulty}
                      </span>
                    </div>

                    <h4
                      className={`text-sm font-bold ${
                        isDone ? 'text-gray-600 line-through' : 'text-gray-900'
                      }`}
                    >
                      {item.topic_name}
                    </h4>

                    {item.unit_name && (
                      <p className="text-xs text-gray-500 mt-0.5">{item.unit_name}</p>
                    )}

                    {isBlocked && (
                      <div className="mt-2 flex items-center space-x-1.5 text-xs text-amber-700 bg-amber-100/60 px-2 py-0.5 rounded-md">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                        <span>Prerequisites pending: {item.unmet_prerequisites.join(', ')}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center space-x-2 flex-shrink-0">
                    <Link
                      to={
                        courseId
                          ? `/courses/${courseId}/topics/${item.topic_id}/tutor?plan_item_id=${item.id}`
                          : `/tutor?topic_id=${item.topic_id}&plan_item_id=${item.id}`
                      }
                      className="inline-flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors shadow-2xs"
                      title="Launch AI Tutor for this topic"
                    >
                      <Bot className="w-3.5 h-3.5" />
                      <span>Tutor</span>
                    </Link>

                    <span className="inline-flex items-center space-x-1 text-xs font-medium text-gray-600 bg-gray-100 px-2.5 py-1 rounded-md">
                      <Clock className="w-3 h-3 text-gray-500" />
                      <span>{item.duration_minutes}m</span>
                    </span>

                    {!isDone ? (
                      <button
                        type="button"
                        onClick={() =>
                          onUpdateStatus(
                            item.id,
                            isInProgress ? 'COMPLETED' : 'IN_PROGRESS'
                          )
                        }
                        className={`inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                          isInProgress
                            ? 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-xs'
                            : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-xs'
                        }`}
                      >
                        {isInProgress ? (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Finish</span>
                          </>
                        ) : (
                          <>
                            <Play className="w-3 h-3 fill-current" />
                            <span>Start</span>
                          </>
                        )}
                      </button>
                    ) : (
                      <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-semibold text-emerald-800 bg-emerald-100">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Mastered</span>
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Down Arrow between steps */}
              {index < sortedSessions.length - 1 && (
                <div className="flex justify-center -mb-2 mt-1 ml-3 text-gray-300">
                  <ArrowDown className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

