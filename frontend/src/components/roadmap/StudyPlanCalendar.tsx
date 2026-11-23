import React from 'react';
import { Calendar, Flag, Sparkles, CheckCircle2 } from 'lucide-react';
import { DayScheduleGroup, PlanItemStatus } from '../../types';
import { StudySessionCard } from './StudySessionCard';

interface StudyPlanCalendarProps {
  days: DayScheduleGroup[];
  dailyMinutesTarget: number;
  courseId?: string;
  onUpdateSessionStatus: (sessionId: string, newStatus: PlanItemStatus) => Promise<void>;
}

export const StudyPlanCalendar: React.FC<StudyPlanCalendarProps> = ({
  days,
  dailyMinutesTarget,
  courseId,
  onUpdateSessionStatus,
}) => {
  const formatDateLabel = (dateStr: string) => {
    try {
      const d = new Date(dateStr + 'T00:00:00');
      return d.toLocaleDateString(undefined, {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  if (!days || days.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500">
        <Calendar className="w-8 h-8 mx-auto text-gray-300 mb-2" />
        <p className="text-sm">No scheduled sessions found for this plan.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {days.map((dayGroup) => {
        const isAllDone =
          dayGroup.sessions.length > 0 &&
          dayGroup.sessions.every((s) => s.status === 'COMPLETED' || s.status === 'SKIPPED');

        return (
          <div
            key={dayGroup.date}
            className={`rounded-xl border transition-all ${
              dayGroup.is_exam_day
                ? 'bg-red-50/40 border-red-300'
                : dayGroup.is_final_revision_day
                ? 'bg-purple-50/30 border-purple-200'
                : 'bg-white border-gray-200'
            } shadow-xs p-5`}
          >
            {/* Day Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 mb-4 border-b border-gray-100">
              <div className="flex items-center space-x-3">
                <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-50 text-indigo-700 text-xs font-bold">
                  D{dayGroup.day_number}
                </span>

                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="text-sm font-bold text-gray-900">
                      {formatDateLabel(dayGroup.date)}
                    </h3>

                    {dayGroup.is_exam_day && (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-2xs font-bold bg-red-100 text-red-800 border border-red-300">
                        <Flag className="w-3 h-3" />
                        <span>EXAM DAY</span>
                      </span>
                    )}

                    {dayGroup.is_final_revision_day && (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-2xs font-semibold bg-purple-100 text-purple-800 border border-purple-200">
                        <Sparkles className="w-3 h-3 text-purple-600" />
                        <span>Final Revision Buffer</span>
                      </span>
                    )}

                    {isAllDone && (
                      <span className="inline-flex items-center space-x-1 text-2xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Day Complete</span>
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Day Time Budget */}
              <div className="flex items-center space-x-2 text-xs">
                <span className="text-gray-500">Scheduled:</span>
                <span
                  className={`font-semibold ${
                    dayGroup.total_minutes > dailyMinutesTarget
                      ? 'text-red-600'
                      : 'text-gray-900'
                  }`}
                >
                  {dayGroup.total_minutes} min
                </span>
                <span className="text-gray-400">/ {dailyMinutesTarget}m target</span>
              </div>
            </div>

            {/* Day Sessions List */}
            <div className="space-y-3">
              {dayGroup.sessions.map((session) => (
                <StudySessionCard
                  key={session.id}
                  session={session}
                  courseId={courseId}
                  onUpdateStatus={onUpdateSessionStatus}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
};

