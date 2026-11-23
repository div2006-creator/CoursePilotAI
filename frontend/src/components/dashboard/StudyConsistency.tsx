import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { Flame, Calendar } from 'lucide-react';
import { StudyConsistencyData } from '../../types';

interface StudyConsistencyProps {
  consistency: StudyConsistencyData;
}

export const StudyConsistency: React.FC<StudyConsistencyProps> = ({ consistency }) => {
  return (
    <div className="bg-white rounded-xl p-5 border border-gray-100 shadow-sm space-y-5">
      {/* Header and Streak */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-gray-900">Study Consistency &amp; Habits</h3>
            <span
              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                consistency.current_streak_days > 0
                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                  : 'bg-gray-100 text-gray-500'
              }`}
            >
              <Flame className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
              {consistency.current_streak_days}-Day Streak
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{consistency.streak_description}</p>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div>
            <span className="text-gray-400 block">Plan Completion</span>
            <span className="font-bold text-gray-900 text-sm">{consistency.completion_rate}%</span>
          </div>
          <div className="h-6 w-px bg-gray-200" />
          <div>
            <span className="text-gray-400 block">Active Days</span>
            <span className="font-bold text-gray-900 text-sm">
              {consistency.active_study_days} day{consistency.active_study_days === 1 ? '' : 's'}
            </span>
          </div>
        </div>
      </div>

      {/* Stats Breakdown */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
          <span className="text-gray-400 block">Scheduled Sessions</span>
          <span className="text-lg font-bold text-gray-900 mt-1 block">
            {consistency.total_scheduled}
          </span>
          <span className="text-[11px] text-gray-500">From adaptive study plan</span>
        </div>

        <div className="p-3 bg-emerald-50/60 rounded-lg border border-emerald-100">
          <span className="text-emerald-700 block font-medium">Completed</span>
          <span className="text-lg font-bold text-emerald-900 mt-1 block">
            {consistency.completed_sessions}
          </span>
          <span className="text-[11px] text-emerald-600">Finished study tasks</span>
        </div>

        <div className="p-3 bg-amber-50/60 rounded-lg border border-amber-100">
          <span className="text-amber-700 block font-medium">Pending</span>
          <span className="text-lg font-bold text-amber-900 mt-1 block">
            {consistency.pending_sessions}
          </span>
          <span className="text-[11px] text-amber-600">Upcoming in study plan</span>
        </div>

        <div className="p-3 bg-rose-50/60 rounded-lg border border-rose-100">
          <span className="text-rose-700 block font-medium">Skipped</span>
          <span className="text-lg font-bold text-rose-900 mt-1 block">
            {consistency.skipped_sessions}
          </span>
          <span className="text-[11px] text-rose-600">Rescheduled or missed</span>
        </div>
      </div>

      {/* Daily Activity Chart */}
      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Daily Study Effort (Minutes &amp; Completed Sessions)
        </h4>
        {consistency.daily_activity.length > 0 ? (
          <div className="h-52 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={consistency.daily_activity}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  unit="m"
                />
                <Tooltip
                  formatter={(value: number, name: string) => [
                    name === 'minutes_spent' ? `${value} min` : value,
                    name === 'minutes_spent' ? 'Minutes Spent' : 'Completed Sessions',
                  ]}
                  labelFormatter={(label) => `Date: ${label}`}
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    borderRadius: '0.5rem',
                    border: '1px solid #e2e8f0',
                    fontSize: '12px',
                  }}
                />
                <Bar
                  dataKey="minutes_spent"
                  name="minutes_spent"
                  fill="#4f46e5"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-36 flex flex-col items-center justify-center border border-dashed border-gray-200 rounded-lg text-center p-4">
            <Calendar className="w-7 h-7 text-gray-300 mb-1.5" />
            <p className="text-xs font-medium text-gray-700">No Daily Activity Logged Yet</p>
            <p className="text-[11px] text-gray-400 max-w-sm mt-0.5">
              Completed study sessions and tutor practice attempts will automatically populate your daily activity graph.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default StudyConsistency;
