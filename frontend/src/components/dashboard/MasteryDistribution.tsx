import React from 'react';
import { CheckCircle2, AlertCircle, HelpCircle, AlertTriangle } from 'lucide-react';
import { CourseOverviewData } from '../../types';

interface MasteryDistributionProps {
  overview: CourseOverviewData;
}

export const MasteryDistribution: React.FC<MasteryDistributionProps> = ({ overview }) => {
  const total = overview.total_topics || 1;
  const strongPct = Math.round((overview.strong_topics / total) * 100);
  const devPct = Math.round((overview.developing_topics / total) * 100);
  const weakPct = Math.round((overview.weak_topics / total) * 100);
  const unassessedPct = Math.round((overview.unassessed_topics / total) * 100);

  return (
    <div className="bg-white rounded-xl p-5 border border-gray-100 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900">Topic Mastery Distribution</h3>
          <p className="text-xs text-gray-500">
            Real mastery classification across all {overview.total_topics} topics in this course
          </p>
        </div>
        <span className="text-xs font-medium text-gray-400">Deterministic thresholds</span>
      </div>

      {/* Stacked Progress Bar */}
      <div className="w-full h-4 bg-gray-100 rounded-full overflow-hidden flex shadow-inner">
        {overview.strong_topics > 0 && (
          <div
            className="bg-emerald-500 h-full transition-all duration-500 hover:opacity-90"
            style={{ width: `${(overview.strong_topics / total) * 100}%` }}
            title={`Strong: ${overview.strong_topics} topics (${strongPct}%)`}
          />
        )}
        {overview.developing_topics > 0 && (
          <div
            className="bg-amber-500 h-full transition-all duration-500 hover:opacity-90"
            style={{ width: `${(overview.developing_topics / total) * 100}%` }}
            title={`Developing: ${overview.developing_topics} topics (${devPct}%)`}
          />
        )}
        {overview.weak_topics > 0 && (
          <div
            className="bg-rose-500 h-full transition-all duration-500 hover:opacity-90"
            style={{ width: `${(overview.weak_topics / total) * 100}%` }}
            title={`Weak: ${overview.weak_topics} topics (${weakPct}%)`}
          />
        )}
        {overview.unassessed_topics > 0 && (
          <div
            className="bg-gray-300 h-full transition-all duration-500 hover:opacity-90"
            style={{ width: `${(overview.unassessed_topics / total) * 100}%` }}
            title={`Unassessed: ${overview.unassessed_topics} topics (${unassessedPct}%)`}
          />
        )}
      </div>

      {/* Category breakdown cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
        {/* Strong */}
        <div className="p-3 rounded-lg border border-emerald-100 bg-emerald-50/50">
          <div className="flex items-center gap-1.5 text-emerald-700">
            <CheckCircle2 className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Strong</span>
          </div>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-xl font-bold text-emerald-900">{overview.strong_topics}</span>
            <span className="text-xs font-medium text-emerald-700">{strongPct}%</span>
          </div>
          <p className="mt-1 text-[11px] text-emerald-600">Mastery &ge; 80%</p>
        </div>

        {/* Developing */}
        <div className="p-3 rounded-lg border border-amber-100 bg-amber-50/50">
          <div className="flex items-center gap-1.5 text-amber-700">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Developing</span>
          </div>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-xl font-bold text-amber-900">{overview.developing_topics}</span>
            <span className="text-xs font-medium text-amber-700">{devPct}%</span>
          </div>
          <p className="mt-1 text-[11px] text-amber-600">Mastery 50% &ndash; 79%</p>
        </div>

        {/* Weak */}
        <div className="p-3 rounded-lg border border-rose-100 bg-rose-50/50">
          <div className="flex items-center gap-1.5 text-rose-700">
            <AlertCircle className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Weak</span>
          </div>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-xl font-bold text-rose-900">{overview.weak_topics}</span>
            <span className="text-xs font-medium text-rose-700">{weakPct}%</span>
          </div>
          <p className="mt-1 text-[11px] text-rose-600">Mastery &lt; 50%</p>
        </div>

        {/* Unassessed */}
        <div className="p-3 rounded-lg border border-gray-200 bg-gray-50/60">
          <div className="flex items-center gap-1.5 text-gray-600">
            <HelpCircle className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Unassessed</span>
          </div>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-xl font-bold text-gray-800">{overview.unassessed_topics}</span>
            <span className="text-xs font-medium text-gray-500">{unassessedPct}%</span>
          </div>
          <p className="mt-1 text-[11px] text-gray-500">No attempts yet</p>
        </div>
      </div>
    </div>
  );
};

export default MasteryDistribution;

