import React from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  Calendar,
  Layers,
} from 'lucide-react';
import { RecommendationItem } from '../../types';

interface RecommendationListProps {
  recommendations: RecommendationItem[];
}

export const RecommendationList: React.FC<RecommendationListProps> = ({ recommendations }) => {
  const getActionIcon = (type: string) => {
    switch (type.toUpperCase()) {
      case 'TUTOR':
        return <BrainCircuit className="w-4 h-4 text-indigo-600" />;
      case 'PRACTICE':
        return <CheckCircle2 className="w-4 h-4 text-emerald-600" />;
      case 'DIAGNOSTIC':
        return <Layers className="w-4 h-4 text-amber-600" />;
      default:
        return <Calendar className="w-4 h-4 text-blue-600" />;
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority.toUpperCase()) {
      case 'HIGH':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'MEDIUM':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      default:
        return 'bg-blue-50 text-blue-700 border-blue-200';
    }
  };

  return (
    <div className="bg-white rounded-xl p-5 border border-gray-100 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-gray-900">Recommended Next Actions</h3>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
              <Sparkles className="w-3 h-3" /> Prioritized
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            Tailored next steps prioritized by prerequisite impact, upcoming deadlines, and mastery gaps
          </p>
        </div>
      </div>

      {recommendations.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {recommendations.map((rec) => (
            <div
              key={rec.id}
              className="p-4 rounded-xl border border-gray-100 bg-gray-50/50 hover:bg-white hover:border-indigo-200 hover:shadow-sm transition-all flex flex-col justify-between space-y-3 text-xs"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-white rounded-lg border border-gray-200">
                      {getActionIcon(rec.action_type)}
                    </div>
                    <span className="font-bold text-gray-900 text-sm line-clamp-1">
                      {rec.title}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold border uppercase shrink-0 ${getPriorityBadge(
                      rec.priority
                    )}`}
                  >
                    {rec.priority}
                  </span>
                </div>

                <p className="text-gray-600 line-clamp-2">{rec.description}</p>

                <div className="p-2 bg-white rounded-lg border border-gray-100 text-[11px] text-gray-500">
                  <span className="font-semibold text-gray-700">Reason:</span> {rec.reason}
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-gray-100">
                <span className="text-[11px] text-gray-400 truncate max-w-[180px]">
                  {rec.supporting_evidence}
                </span>
                <Link
                  to={rec.action_url}
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold transition-colors"
                >
                  <span>Start Now</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-4 text-center text-xs text-gray-500 border border-dashed border-gray-200 rounded-lg">
          No immediate actions required. Continue exploring topics or practicing with the AI Tutor.
        </div>
      )}
    </div>
  );
};

export default RecommendationList;
