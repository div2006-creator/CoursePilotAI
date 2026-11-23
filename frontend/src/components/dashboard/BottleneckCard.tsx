import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, ArrowRight, CheckCircle2, GitFork } from 'lucide-react';
import { PrerequisiteBlockerItem } from '../../types';

interface BottleneckCardProps {
  bottlenecks: PrerequisiteBlockerItem[];
  courseId: string;
}

export const BottleneckCard: React.FC<BottleneckCardProps> = ({ bottlenecks, courseId }) => {
  return (
    <div className="bg-white rounded-xl p-5 border border-gray-100 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-gray-900">Foundational Bottlenecks</h3>
            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-100">
              {bottlenecks.length} Critical Concept{bottlenecks.length === 1 ? '' : 's'}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            Weak or unassessed prerequisite topics that are currently blocking progression into advanced topics
          </p>
        </div>
        <GitFork className="w-5 h-5 text-gray-400 hidden sm:block" />
      </div>

      {bottlenecks.length > 0 ? (
        <div className="space-y-3">
          {bottlenecks.map((item) => (
            <div
              key={item.topic_id}
              className="p-4 rounded-lg border border-rose-100 bg-rose-50/40 hover:bg-rose-50/70 transition-colors space-y-2 text-xs"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
                  <span className="font-bold text-gray-900 text-sm">{item.topic_name}</span>
                  {item.unit_name && (
                    <span className="text-[11px] text-gray-400">({item.unit_name})</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-white text-rose-700 border border-rose-200">
                    Impact: {item.bottleneck_impact_score}
                  </span>
                  <span className="text-gray-500">
                    Mastery:{' '}
                    <strong className="text-gray-900">
                      {item.mastery_percentage !== null ? `${item.mastery_percentage}%` : 'Unassessed'}
                    </strong>
                  </span>
                </div>
              </div>

              <p className="text-gray-700">{item.explanation}</p>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1 border-t border-rose-100/60">
                <div className="text-[11px] text-gray-500">
                  <span className="font-medium text-gray-700">Blocks {item.dependent_topics_count} topic(s):</span>{' '}
                  {item.blocked_topics_names.slice(0, 3).join(', ')}
                  {item.blocked_topics_names.length > 3 && ` +${item.blocked_topics_names.length - 3} more`}
                </div>
                <Link
                  to={`/courses/${courseId}/topics/${item.topic_id}/tutor`}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded-md text-xs font-semibold transition-colors shrink-0"
                >
                  <span>Tutor Prerequisite</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-4 bg-emerald-50/50 border border-emerald-100 rounded-lg flex items-center gap-3 text-xs text-emerald-800">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <div>
            <p className="font-semibold text-emerald-900">No Prerequisite Bottlenecks Detected</p>
            <p className="text-emerald-700 mt-0.5">
              All foundational concepts with dependent topics have satisfactory mastery. Your learning graph is flowing smoothly.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default BottleneckCard;
