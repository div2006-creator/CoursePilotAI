import React from 'react';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  ShieldCheck,
  Info,
} from 'lucide-react';
import { LearningImprovementData } from '../../types';

interface ImprovementComparisonProps {
  improvement: LearningImprovementData;
}

export const ImprovementComparison: React.FC<ImprovementComparisonProps> = ({ improvement }) => {
  const getQualityBadge = (quality: string) => {
    switch (quality) {
      case 'HIGH':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'MEDIUM':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-600 border-gray-200';
    }
  };

  return (
    <div className="bg-white rounded-xl p-5 border border-gray-100 shadow-sm space-y-4">
      {/* Header and Explanation */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-gray-900">
              Verified Learning Improvement
            </h3>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-100">
              <ShieldCheck className="w-3 h-3" /> Fresh Questions Only
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Comparing initial diagnostic baseline performance with subsequent fresh assessment
            attempts. Repeated or identical questions are strictly excluded from post-learning scores.
          </p>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
          <span className="text-xs text-gray-500 font-medium">Compared Topics</span>
          <div className="mt-1 text-xl font-bold text-gray-900">
            {improvement.total_comparisons}
          </div>
          <span className="text-[11px] text-gray-400">Baseline + Post-diagnostic</span>
        </div>

        <div className="p-3 bg-emerald-50/60 rounded-lg border border-emerald-100">
          <span className="text-xs text-emerald-700 font-medium">Improved Topics</span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-emerald-900">
              {improvement.improved_topics_count}
            </span>
            <TrendingUp className="w-4 h-4 text-emerald-600" />
          </div>
          <span className="text-[11px] text-emerald-600">Higher accuracy on fresh items</span>
        </div>

        <div className="p-3 bg-blue-50/60 rounded-lg border border-blue-100">
          <span className="text-xs text-blue-700 font-medium">Average Improvement</span>
          <div className="mt-1 text-xl font-bold text-blue-900">
            {improvement.average_percentage_point_change !== null
              ? `${improvement.average_percentage_point_change > 0 ? '+' : ''}${improvement.average_percentage_point_change} pp`
              : '—'}
          </div>
          <span className="text-[11px] text-blue-600">Percentage points delta</span>
        </div>

        <div className="p-3 bg-amber-50/60 rounded-lg border border-amber-100">
          <span className="text-xs text-amber-700 font-medium">Stagnant / Regressed</span>
          <div className="mt-1 text-xl font-bold text-amber-900">
            {improvement.stagnant_topics_count + improvement.regressed_topics_count}
          </div>
          <span className="text-[11px] text-amber-600">
            {improvement.regressed_topics_count} regressed, {improvement.stagnant_topics_count} unchanged
          </span>
        </div>
      </div>

      {/* Comparisons List */}
      {improvement.has_sufficient_data && improvement.comparisons.length > 0 ? (
        <div className="space-y-2.5 pt-1">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Topic-by-Topic Before &amp; After Comparison
          </h4>
          <div className="divide-y divide-gray-100 border border-gray-100 rounded-lg overflow-hidden">
            {improvement.comparisons.map((comp) => {
              const delta = comp.percentage_point_improvement;
              return (
                <div
                  key={comp.topic_id}
                  className="p-3 bg-white hover:bg-gray-50/80 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-gray-900 truncate">
                      {comp.topic_name}
                    </div>
                    <div className="text-[11px] text-gray-400 mt-0.5 flex items-center gap-2">
                      <span>Baseline: {comp.baseline_questions_count} questions</span>
                      <span>&bull;</span>
                      <span>Fresh: {comp.latest_questions_count} questions</span>
                      <span>&bull;</span>
                      <span
                        className={`px-1.5 py-0.2 rounded border text-[10px] ${getQualityBadge(
                          comp.evidence_quality
                        )}`}
                      >
                        {comp.evidence_quality} Evidence
                      </span>
                    </div>
                  </div>

                  {/* Before vs After Scores */}
                  <div className="flex items-center gap-4 text-right sm:text-center">
                    <div>
                      <span className="text-[10px] text-gray-400 block uppercase">Baseline</span>
                      <span className="font-medium text-gray-700">{comp.baseline_score}%</span>
                    </div>
                    <span className="text-gray-300">&rarr;</span>
                    <div>
                      <span className="text-[10px] text-gray-400 block uppercase">Post-Tutoring</span>
                      <span className="font-semibold text-gray-900">
                        {comp.latest_score !== null ? `${comp.latest_score}%` : '—'}
                      </span>
                    </div>

                    {/* Delta Badge */}
                    <div className="min-w-20 text-right">
                      {delta !== null ? (
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold ${
                            delta > 0
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : delta < 0
                              ? 'bg-rose-50 text-rose-700 border border-rose-200'
                              : 'bg-gray-100 text-gray-600 border border-gray-200'
                          }`}
                        >
                          {delta > 0 ? (
                            <TrendingUp className="w-3.5 h-3.5" />
                          ) : delta < 0 ? (
                            <TrendingDown className="w-3.5 h-3.5" />
                          ) : (
                            <Minus className="w-3.5 h-3.5" />
                          )}
                          {delta > 0 ? '+' : ''}
                          {delta} pp
                        </span>
                      ) : (
                        <span className="text-gray-400 italic text-[11px]">Pending Fresh Test</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="p-4 bg-gray-50 border border-dashed border-gray-200 rounded-lg flex items-start gap-3">
          <Info className="w-5 h-5 text-indigo-500 shrink-0 mt-0.5" />
          <div className="text-xs text-gray-600 space-y-1">
            <p className="font-semibold text-gray-900">
              Verified Post-Learning Assessment Comparison Pending
            </p>
            <p>
              To measure genuine learning improvement, complete study sessions with the AI Tutor and
              then take practice questions or targeted diagnostic assessments on those topics.
            </p>
            <p className="text-gray-400 text-[11px]">
              {improvement.explanation}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ImprovementComparison;
