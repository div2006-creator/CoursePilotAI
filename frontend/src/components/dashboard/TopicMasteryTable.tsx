import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  HelpCircle,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  ShieldAlert,
} from 'lucide-react';
import { TopicMasteryAnalyticsData } from '../../types';

interface TopicMasteryTableProps {
  data: TopicMasteryAnalyticsData;
  courseId: string;
}

export const TopicMasteryTable: React.FC<TopicMasteryTableProps> = ({ data, courseId }) => {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'STRONG' | 'DEVELOPING' | 'WEAK' | 'NOT_ASSESSED'>('ALL');
  const [sortField, setSortField] = useState<'name' | 'mastery' | 'evidence'>('mastery');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const filteredTopics = useMemo(() => {
    return data.topics.filter((topic) => {
      const matchesSearch =
        topic.topic_name.toLowerCase().includes(search.toLowerCase()) ||
        (topic.unit_name && topic.unit_name.toLowerCase().includes(search.toLowerCase()));

      const matchesStatus =
        statusFilter === 'ALL' || topic.learning_status === statusFilter;

      return matchesSearch && matchesStatus;
    }).sort((a, b) => {
      if (sortField === 'name') {
        return sortDirection === 'asc'
          ? a.topic_name.localeCompare(b.topic_name)
          : b.topic_name.localeCompare(a.topic_name);
      }
      if (sortField === 'mastery') {
        const scoreA = a.mastery_score ?? -1;
        const scoreB = b.mastery_score ?? -1;
        return sortDirection === 'asc' ? scoreA - scoreB : scoreB - scoreA;
      }
      if (sortField === 'evidence') {
        return sortDirection === 'asc'
          ? a.evidence_count - b.evidence_count
          : b.evidence_count - a.evidence_count;
      }
      return 0;
    });
  }, [data.topics, search, statusFilter, sortField, sortDirection]);

  const toggleSort = (field: 'name' | 'mastery' | 'evidence') => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection(field === 'mastery' ? 'asc' : 'desc');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'STRONG':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3" /> Strong
          </span>
        );
      case 'DEVELOPING':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3 h-3" /> Developing
          </span>
        );
      case 'WEAK':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3 h-3" /> Weak
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 border border-gray-200">
            <HelpCircle className="w-3 h-3" /> Not Assessed
          </span>
        );
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
      {/* Table Header and Controls */}
      <div className="p-4 sm:p-5 border-b border-gray-100 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-gray-900">Topic Mastery Breakdown</h3>
            <p className="text-xs text-gray-500">
              Granular topic evidence, mastery scores, delta changes, and prerequisite alerts
            </p>
          </div>
          {/* Search bar */}
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search topics or units..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:bg-white"
            />
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <button
            onClick={() => setStatusFilter('ALL')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              statusFilter === 'ALL'
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            All ({data.total_count})
          </button>
          <button
            onClick={() => setStatusFilter('STRONG')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              statusFilter === 'STRONG'
                ? 'bg-emerald-600 text-white'
                : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
            }`}
          >
            Strong ({data.strong_count})
          </button>
          <button
            onClick={() => setStatusFilter('DEVELOPING')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              statusFilter === 'DEVELOPING'
                ? 'bg-amber-600 text-white'
                : 'bg-amber-50 text-amber-700 hover:bg-amber-100'
            }`}
          >
            Developing ({data.developing_count})
          </button>
          <button
            onClick={() => setStatusFilter('WEAK')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              statusFilter === 'WEAK'
                ? 'bg-rose-600 text-white'
                : 'bg-rose-50 text-rose-700 hover:bg-rose-100'
            }`}
          >
            Weak ({data.weak_count})
          </button>
          <button
            onClick={() => setStatusFilter('NOT_ASSESSED')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              statusFilter === 'NOT_ASSESSED'
                ? 'bg-gray-700 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Not Assessed ({data.unassessed_count})
          </button>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-gray-600">
          <thead className="bg-gray-50/75 border-b border-gray-100 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
            <tr>
              <th
                onClick={() => toggleSort('name')}
                className="py-3 px-4 cursor-pointer hover:text-gray-700"
              >
                Topic & Unit
              </th>
              <th className="py-3 px-4">Difficulty</th>
              <th className="py-3 px-4">Status</th>
              <th
                onClick={() => toggleSort('mastery')}
                className="py-3 px-4 cursor-pointer hover:text-gray-700"
              >
                Mastery Score
              </th>
              <th className="py-3 px-4">Change</th>
              <th
                onClick={() => toggleSort('evidence')}
                className="py-3 px-4 cursor-pointer hover:text-gray-700"
              >
                Evidence
              </th>
              <th className="py-3 px-4">Prerequisites</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredTopics.length > 0 ? (
              filteredTopics.map((topic) => (
                <tr key={topic.topic_id} className="hover:bg-gray-50/80 transition-colors">
                  <td className="py-3 px-4 font-medium text-gray-900 max-w-xs">
                    <div className="truncate font-semibold">{topic.topic_name}</div>
                    {topic.unit_name && (
                      <div className="text-[11px] text-gray-400 truncate">{topic.unit_name}</div>
                    )}
                  </td>
                  <td className="py-3 px-4 capitalize">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium ${
                        topic.difficulty.toLowerCase() === 'hard'
                          ? 'bg-purple-50 text-purple-700 border border-purple-200'
                          : topic.difficulty.toLowerCase() === 'medium'
                          ? 'bg-blue-50 text-blue-700 border border-blue-200'
                          : 'bg-teal-50 text-teal-700 border border-teal-200'
                      }`}
                    >
                      {topic.difficulty}
                    </span>
                  </td>
                  <td className="py-3 px-4">{getStatusBadge(topic.learning_status)}</td>
                  <td className="py-3 px-4 font-semibold">
                    {topic.mastery_percentage !== null ? (
                      <span
                        className={
                          topic.mastery_percentage >= 80
                            ? 'text-emerald-700'
                            : topic.mastery_percentage >= 50
                            ? 'text-amber-700'
                            : 'text-rose-700'
                        }
                      >
                        {topic.mastery_percentage}%
                      </span>
                    ) : (
                      <span className="text-gray-400 font-normal italic">Not assessed</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    {topic.mastery_change !== null ? (
                      <span
                        className={`inline-flex items-center gap-0.5 font-medium ${
                          topic.mastery_change > 0
                            ? 'text-emerald-600'
                            : topic.mastery_change < 0
                            ? 'text-rose-600'
                            : 'text-gray-400'
                        }`}
                      >
                        {topic.mastery_change > 0 ? (
                          <TrendingUp className="w-3 h-3" />
                        ) : topic.mastery_change < 0 ? (
                          <TrendingDown className="w-3 h-3" />
                        ) : null}
                        {topic.mastery_change > 0 ? '+' : ''}
                        {topic.mastery_change} pp
                      </span>
                    ) : (
                      <span className="text-gray-300">&mdash;</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className="text-gray-700 font-medium">{topic.evidence_count}</span>
                    <span className="text-gray-400 text-[11px] ml-1">attempts</span>
                  </td>
                  <td className="py-3 px-4">
                    {topic.is_prerequisite_satisfied ? (
                      <span className="text-emerald-600 flex items-center gap-1 text-[11px]">
                        <CheckCircle2 className="w-3 h-3" /> Ready
                      </span>
                    ) : (
                      <span
                        className="text-rose-600 flex items-center gap-1 text-[11px]"
                        title={`Blocked by unmet prerequisites: ${topic.unmet_prerequisites.join(', ')}`}
                      >
                        <ShieldAlert className="w-3 h-3" /> Blocked ({topic.unmet_prerequisites.length})
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <Link
                      to={`/courses/${courseId}/topics/${topic.topic_id}/tutor`}
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-md transition-colors"
                    >
                      <span>Tutor</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={8} className="py-8 text-center text-gray-400">
                  No topics matching the selected filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TopicMasteryTable;
