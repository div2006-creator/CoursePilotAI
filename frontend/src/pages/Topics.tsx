import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  GitFork,
  Layers,
  Loader2,
  Pencil,
  RefreshCw,
  Search,
  Sparkles,
  Tag,
  Trash2,
  X,
} from 'lucide-react';
import { CourseTopicsData, Topic, TopicDetail, TopicUpdatePayload } from '../types';
import { topicService } from '../services/topicService';
import { courseService } from '../services/courseService';
import { extractApiErrorMessage } from '../services/api';
import { EditTopicModal, DeleteTopicModal } from '../components/topic';

const DIFFICULTY_META: Record<string, { label: string; className: string }> = {
  easy: { label: 'Easy', className: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  medium: { label: 'Medium', className: 'bg-amber-50 text-amber-700 border-amber-200' },
  hard: { label: 'Hard', className: 'bg-rose-50 text-rose-700 border-rose-200' },
};

export const Topics: React.FC = () => {
  const { courseId } = useParams<{ courseId: string }>();

  const [courseTitle, setCourseTitle] = useState<string>('Course');
  const [topicsData, setTopicsData] = useState<CourseTopicsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // AI Extraction state
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);

  // Modals state
  const [editingTopic, setEditingTopic] = useState<Topic | TopicDetail | null>(null);
  const [deletingTopic, setDeletingTopic] = useState<Topic | TopicDetail | null>(null);

  const fetchTopics = useCallback(async () => {
    if (!courseId) return;
    setIsLoading(true);
    setLoadError(null);
    try {
      const [courseRes, topicsRes] = await Promise.all([
        courseService.getCourseById(courseId),
        topicService.getCourseTopics(courseId),
      ]);
      setCourseTitle(courseRes.data.title);
      setTopicsData(topicsRes.data);
    } catch (err) {
      setLoadError(
        extractApiErrorMessage(err, 'Failed to load topics for this course.')
      );
    } finally {
      setIsLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    void fetchTopics();
  }, [fetchTopics]);

  const handleExtractTopics = async () => {
    if (!courseId) return;
    setIsExtracting(true);
    setExtractError(null);
    setNotice(null);
    try {
      const res = await topicService.extractTopics(courseId);
      setNotice(
        `AI extracted ${res.data.topics_created} topics and ${res.data.prerequisites_created} prerequisite relationships!`
      );
      await fetchTopics();
    } catch (err) {
      setExtractError(
        extractApiErrorMessage(err, 'Topic extraction failed. Please ensure syllabus documents are uploaded.')
      );
    } finally {
      setIsExtracting(false);
    }
  };

  const handleUpdateTopic = async (payload: TopicUpdatePayload) => {
    if (!editingTopic) return;
    await topicService.updateTopic(editingTopic.id, payload);
    setNotice(`Topic "${payload.name || editingTopic.name}" updated successfully.`);
    await fetchTopics();
  };

  const handleDeleteTopic = async (target: Topic | TopicDetail) => {
    await topicService.deleteTopic(target.id);
    setNotice(`Topic "${target.name}" was deleted.`);
    await fetchTopics();
  };

  // Filtered units and topics
  const filteredUnits = useMemo(() => {
    if (!topicsData) return [];
    const q = searchQuery.trim().toLowerCase();
    if (!q) return topicsData.units;

    return topicsData.units
      .map((unit) => {
        const matchingTopics = unit.topics.filter(
          (t) =>
            t.name.toLowerCase().includes(q) ||
            (t.description && t.description.toLowerCase().includes(q)) ||
            t.subtopics.some((s) => s.name.toLowerCase().includes(q))
        );
        return {
          ...unit,
          topics: matchingTopics,
        };
      })
      .filter((unit) => unit.topics.length > 0);
  }, [topicsData, searchQuery]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link
            to={`/courses/${courseId}`}
            className="inline-flex items-center space-x-1.5 text-xs font-medium text-gray-500 hover:text-indigo-600 transition-colors mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to {courseTitle}</span>
          </Link>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
              Syllabus Topics
            </h1>
            {topicsData && topicsData.total_topics > 0 && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-100">
                {topicsData.total_topics} topics
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Review, edit, and organize extracted topics, subtopics, and prerequisite hierarchy.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 self-start sm:self-auto">
          <Link
            to={`/courses/${courseId}/graph`}
            className="inline-flex items-center space-x-1.5 rounded-lg border border-gray-300 bg-white px-3.5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:text-indigo-600 transition-colors shadow-sm"
          >
            <GitFork className="w-4 h-4 text-indigo-600" />
            <span>Knowledge Graph</span>
          </Link>
          <button
            type="button"
            onClick={handleExtractTopics}
            disabled={isExtracting}
            className="inline-flex items-center space-x-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-60 transition-colors"
          >
            {isExtracting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4 text-amber-300" />
            )}
            <span>{isExtracting ? 'Extracting with AI...' : 'Extract Topics with AI'}</span>
          </button>
        </div>
      </div>

      {notice && (
        <div
          role="status"
          className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
        >
          <div className="flex items-center space-x-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{notice}</span>
          </div>
          <button
            type="button"
            onClick={() => setNotice(null)}
            className="p-1 rounded text-emerald-700 hover:bg-emerald-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {extractError && (
        <div
          role="alert"
          className="flex items-start space-x-2.5 rounded-lg border border-red-200 bg-red-50 p-3.5 text-sm text-red-700"
        >
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <span className="font-semibold">Extraction notice: </span>
            <span>{extractError}</span>
          </div>
          <button
            type="button"
            onClick={() => setExtractError(null)}
            className="p-1 rounded text-red-700 hover:bg-red-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {topicsData && topicsData.total_topics > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Units</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{topicsData.total_units}</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Total Topics</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{topicsData.total_topics}</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Tag className="w-5 h-5" />
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Subtopics</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{topicsData.total_subtopics}</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <GitFork className="w-5 h-5" />
            </div>
          </div>
        </div>
      )}

      {topicsData && topicsData.total_topics > 0 && (
        <div className="relative max-w-md">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search topics or subtopics..."
            className="w-full rounded-lg border border-gray-300 bg-white pl-9 pr-9 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 flex flex-col items-center justify-center text-center">
          <Loader2 className="w-7 h-7 text-indigo-600 animate-spin" />
          <p className="mt-3 text-sm font-medium text-gray-700">Loading syllabus topics...</p>
        </div>
      ) : loadError ? (
        <div className="bg-white rounded-xl border border-red-200 p-8 text-center max-w-xl mx-auto">
          <AlertCircle className="w-7 h-7 text-red-600 mx-auto" />
          <h2 className="mt-3 text-base font-semibold text-gray-900">Failed to load topics</h2>
          <p className="mt-1 text-sm text-gray-500">{loadError}</p>
          <button
            type="button"
            onClick={() => void fetchTopics()}
            className="mt-4 inline-flex items-center space-x-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Try Again</span>
          </button>
        </div>
      ) : !topicsData || topicsData.total_topics === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm max-w-xl mx-auto">
          <div className="mx-auto w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <Layers className="w-6 h-6" />
          </div>
          <h2 className="mt-4 text-lg font-semibold text-gray-900">No Topics Extracted Yet</h2>
          <p className="mt-1.5 text-sm text-gray-500 leading-relaxed">
            Upload your syllabus or lecture documents, then click <strong>Extract Topics with AI</strong> to automatically parse units, concepts, and prerequisite relationships.
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Link
              to={`/courses/${courseId}`}
              className="inline-flex items-center space-x-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <span>Upload Documents First</span>
            </Link>
            <button
              type="button"
              onClick={handleExtractTopics}
              disabled={isExtracting}
              className="inline-flex items-center space-x-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-60"
            >
              {isExtracting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4 text-amber-300" />
              )}
              <span>{isExtracting ? 'Extracting with AI...' : 'Extract Topics with AI'}</span>
            </button>
          </div>
        </div>
      ) : filteredUnits.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <Search className="w-8 h-8 text-gray-300 mx-auto" />
          <p className="mt-2 text-sm font-medium text-gray-700">No topics match &ldquo;{searchQuery}&rdquo;</p>
          <button
            type="button"
            onClick={() => setSearchQuery('')}
            className="mt-3 text-xs font-medium text-indigo-600 hover:underline"
          >
            Clear search
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {filteredUnits.map((unit) => (
            <section
              key={unit.unit_name}
              className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
            >
              <div className="bg-gray-50/80 px-6 py-3.5 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <Layers className="w-4 h-4 text-indigo-600" />
                  <h2 className="text-base font-semibold text-gray-900">{unit.unit_name}</h2>
                </div>
                <span className="text-xs font-medium text-gray-500">
                  {unit.topics.length} {unit.topics.length === 1 ? 'topic' : 'topics'}
                </span>
              </div>

              <div className="divide-y divide-gray-100">
                {unit.topics.map((topic) => {
                  const diffMeta = DIFFICULTY_META[topic.difficulty] || DIFFICULTY_META.medium;
                  return (
                    <article key={topic.id} className="p-6 hover:bg-gray-50/40 transition-colors">
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                        <div className="space-y-1.5 max-w-2xl">
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-base font-semibold text-gray-900">{topic.name}</h3>
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${diffMeta.className}`}
                            >
                              {diffMeta.label}
                            </span>
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                                topic.source_type === 'explicit'
                                  ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                                  : 'bg-purple-50 text-purple-700 border-purple-200'
                              }`}
                            >
                              {topic.source_type === 'explicit' ? 'Explicit Syllabus' : 'AI Inferred'}
                            </span>
                            {topic.source_pages && topic.source_pages.length > 0 && (
                              <span className="inline-flex items-center space-x-1 text-xs text-gray-400">
                                <span>Pages: {topic.source_pages.join(', ')}</span>
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 leading-relaxed">
                            {topic.description || (
                              <span className="text-gray-400 italic">No description provided.</span>
                            )}
                          </p>
                        </div>

                        <div className="flex items-center space-x-2 flex-shrink-0">
                          <Link
                            to={`/courses/${courseId}/topics/${topic.id}/tutor`}
                            className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors shadow-2xs"
                            title="Start AI Tutor for this topic"
                          >
                            <Bot className="w-3.5 h-3.5" />
                            <span>Tutor</span>
                          </Link>
                          <button
                            type="button"
                            onClick={() => setEditingTopic(topic)}
                            title="Edit topic"
                            className="p-1.5 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                          >
                            <Pencil className="w-4 h-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => setDeletingTopic(topic)}
                            title="Delete topic"
                            className="p-1.5 rounded-lg text-gray-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      {topic.subtopics && topic.subtopics.length > 0 && (
                        <div className="mt-3.5 pt-3 border-t border-gray-100">
                          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-2">
                            Subtopics ({topic.subtopics.length})
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {topic.subtopics.map((sub) => (
                              <span
                                key={sub.id}
                                className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-700 border border-gray-200"
                                title={sub.description || sub.name}
                              >
                                {sub.name}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </article>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}

      <EditTopicModal
        isOpen={Boolean(editingTopic)}
        topic={editingTopic}
        onClose={() => setEditingTopic(null)}
        onSubmit={handleUpdateTopic}
      />

      <DeleteTopicModal
        topic={deletingTopic}
        onClose={() => setDeletingTopic(null)}
        onConfirm={handleDeleteTopic}
      />
    </div>
  );
};

export default Topics;
