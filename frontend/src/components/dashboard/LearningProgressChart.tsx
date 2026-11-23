import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import {
  TrendingUp,
  Zap,
  Clock,
  Sparkles,
} from 'lucide-react';
import { LearningProgressData } from '../../types';

interface LearningProgressChartProps {
  progress: LearningProgressData;
}

export const LearningProgressChart: React.FC<LearningProgressChartProps> = ({ progress }) => {
  const { history_points, velocity } = progress;

  const getVelocityBadge = (status: string) => {
    switch (status) {
      case 'ACCELERATING':
        return {
          bg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
          dot: 'bg-emerald-500',
          label: 'Accelerating',
        };
      case 'STEADY':
        return {
          bg: 'bg-blue-50 text-blue-700 border-blue-200',
          dot: 'bg-blue-500',
          label: 'Steady Progress',
        };
      case 'EARLY_STAGE':
        return {
          bg: 'bg-indigo-50 text-indigo-700 border-indigo-200',
          dot: 'bg-indigo-500',
          label: 'Early Stage',
        };
      default:
        return {
          bg: 'bg-amber-50 text-amber-700 border-amber-200',
          dot: 'bg-amber-500',
          label: 'Needs Practice',
        };
    }
  };

  const badge = getVelocityBadge(velocity.velocity_status);

  return (
    <div className="bg-white rounded-xl p-5 border border-gray-100 shadow-sm space-y-5">
      {/* Velocity Status Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-gray-900">Longitudinal Learning Velocity</h3>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${badge.bg}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`} />
              {badge.label}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{velocity.velocity_description}</p>
        </div>

        {/* Velocity Key Counters */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-xs text-gray-400 block">7-Day Momentum</span>
            <span className="text-sm font-semibold text-emerald-600">
              +{velocity.topics_improved_7d} topic{velocity.topics_improved_7d === 1 ? '' : 's'}
            </span>
          </div>
          <div className="h-7 w-px bg-gray-200" />
          <div className="text-right">
            <span className="text-xs text-gray-400 block">30-Day Momentum</span>
            <span className="text-sm font-semibold text-blue-600">
              +{velocity.topics_improved_30d} topic{velocity.topics_improved_30d === 1 ? '' : 's'}
            </span>
          </div>
        </div>
      </div>

      {/* Graduation Transitions Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100 text-xs">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-500" />
          <div>
            <span className="font-medium text-gray-700">Weak &rarr; Developing:</span>{' '}
            <span className="font-bold text-gray-900">
              {velocity.transitions_weak_to_developing} topic{velocity.transitions_weak_to_developing === 1 ? '' : 's'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-500" />
          <div>
            <span className="font-medium text-gray-700">Developing &rarr; Strong:</span>{' '}
            <span className="font-bold text-gray-900">
              {velocity.transitions_developing_to_strong} topic{velocity.transitions_developing_to_strong === 1 ? '' : 's'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-indigo-500" />
          <div>
            <span className="font-medium text-gray-700">Average Delta:</span>{' '}
            <span className="font-bold text-gray-900">
              {velocity.average_mastery_change !== null
                ? `${velocity.average_mastery_change > 0 ? '+' : ''}${velocity.average_mastery_change} pp`
                : '—'}
            </span>
          </div>
        </div>
      </div>

      {/* Chart Section */}
      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Mastery Progression Over Time
        </h4>
        {history_points.length >= 2 ? (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history_points} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="masteryGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis
                  domain={[0, 100]}
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  unit="%"
                />
                <Tooltip
                  formatter={(value: number) => [`${value}%`, 'Average Mastery']}
                  labelFormatter={(label) => `Date: ${label}`}
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    borderRadius: '0.5rem',
                    border: '1px solid #e2e8f0',
                    fontSize: '12px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="average_mastery"
                  stroke="#4f46e5"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#masteryGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-44 flex flex-col items-center justify-center border border-dashed border-gray-200 rounded-lg text-center p-4">
            <Clock className="w-8 h-8 text-gray-300 mb-2" />
            <p className="text-sm font-medium text-gray-700">Longitudinal Timeline Building</p>
            <p className="text-xs text-gray-400 max-w-sm mt-1">
              Historical progress points appear as you complete study sessions across different days.
              {history_points.length === 1 && ' 1 snapshot recorded so far.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default LearningProgressChart;
