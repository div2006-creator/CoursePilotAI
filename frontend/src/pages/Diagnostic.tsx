import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useLocation, Link } from 'react-router-dom';
import {
  ArrowLeft,
  BrainCircuit,
  CheckCircle2,
  HelpCircle,
  Play,
  Sparkles,
} from 'lucide-react';
import {
  AssessmentProgress,
  AssessmentTimer,
  QuestionCard,
  QuestionNavigation,
  SubmitConfirmationModal,
} from '../components/quiz';
import { startDiagnostic, submitDiagnostic } from '../services/diagnosticService';
import { getCourseById } from '../services/courseService';
import { getCourseTopics } from '../services/topicService';
import {
  Course,
  DiagnosticQuestionsData,
  Topic,
  UnitGroup,
} from '../types';
import { extractApiErrorMessage } from '../services/api';

export const Diagnostic: React.FC = () => {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  // Course & Topic State
  const [course, setCourse] = useState<Course | null>(null);
  const [availableTopics, setAvailableTopics] = useState<Topic[]>([]);
  const [isLoadingSetup, setIsLoadingSetup] = useState(true);
  const [setupError, setSetupError] = useState<string | null>(null);

  // Assessment Configuration State
  const [mode, setMode] = useState<'full' | 'selected'>('full');
  const [selectedTopicIds, setSelectedTopicIds] = useState<string[]>([]);
  const [difficulty, setDifficulty] = useState<'mixed' | 'easy' | 'medium' | 'hard'>('mixed');
  const [questionsPerTopic, setQuestionsPerTopic] = useState(2);
  const [isStarting, setIsStarting] = useState(false);

  // Active Assessment State
  const [sessionData, setSessionData] = useState<DiagnosticQuestionsData | null>(() => {
    if (location.state && (location.state as any).sessionData) {
      return (location.state as any).sessionData as DiagnosticQuestionsData;
    }
    return null;
  });
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [timePerQuestion, setTimePerQuestion] = useState<Record<string, number>>({});
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const activeQuestionStartTimeRef = useRef<number>(Date.now());

  // Load course details & topics on mount
  useEffect(() => {
    if (!courseId) return;

    const loadData = async () => {
      setIsLoadingSetup(true);
      setSetupError(null);
      try {
        const [courseRes, topicsRes] = await Promise.all([
          getCourseById(courseId),
          getCourseTopics(courseId),
        ]);
        setCourse(courseRes.data);

        // Flatten all topics from units
        const allTopics: Topic[] = [];
        if (topicsRes.data?.units) {
          topicsRes.data.units.forEach((unit: UnitGroup) => {
            allTopics.push(...unit.topics);
          });
        }
        setAvailableTopics(allTopics);

        // Default all topics selected
        setSelectedTopicIds(allTopics.map((t) => t.id));
      } catch (err) {
        setSetupError(extractApiErrorMessage(err, 'Failed to load course information.'));
      } finally {
        setIsLoadingSetup(false);
      }
    };

    loadData();
  }, [courseId]);

  // Track timing when switching questions
  const recordQuestionTime = () => {
    if (!sessionData) return;
    const currentQ = sessionData.questions[currentQuestionIndex];
    if (!currentQ) return;

    const elapsed = Math.round((Date.now() - activeQuestionStartTimeRef.current) / 1000);
    setTimePerQuestion((prev) => ({
      ...prev,
      [currentQ.id]: (prev[currentQ.id] || 0) + elapsed,
    }));
    activeQuestionStartTimeRef.current = Date.now();
  };

  const handleSelectAnswer = (answer: string) => {
    if (!sessionData) return;
    const currentQ = sessionData.questions[currentQuestionIndex];
    if (!currentQ) return;

    setAnswers((prev) => ({
      ...prev,
      [currentQ.id]: answer,
    }));
  };

  const handleNavigateIndex = (index: number) => {
    recordQuestionTime();
    setCurrentQuestionIndex(index);
  };

  const handleNext = () => {
    if (!sessionData) return;
    if (currentQuestionIndex < sessionData.questions.length - 1) {
      handleNavigateIndex(currentQuestionIndex + 1);
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      handleNavigateIndex(currentQuestionIndex - 1);
    }
  };

  const handleToggleTopic = (topicId: string) => {
    setSelectedTopicIds((prev) =>
      prev.includes(topicId) ? prev.filter((id) => id !== topicId) : [...prev, topicId]
    );
  };

  const handleSelectAllTopics = () => {
    setSelectedTopicIds(availableTopics.map((t) => t.id));
  };

  const handleClearAllTopics = () => {
    setSelectedTopicIds([]);
  };

  // Launch Assessment
  const handleStartAssessment = async () => {
    if (!courseId) return;
    if (mode === 'selected' && selectedTopicIds.length === 0) {
      setSetupError('Please select at least one topic for your diagnostic assessment.');
      return;
    }

    setIsStarting(true);
    setSetupError(null);

    try {
      const data = await startDiagnostic(courseId, {
        mode,
        topic_ids: mode === 'selected' ? selectedTopicIds : undefined,
        difficulty,
        questions_per_topic: questionsPerTopic,
      });

      setSessionData(data);
      setCurrentQuestionIndex(0);
      setAnswers({});
      setTimePerQuestion({});
      activeQuestionStartTimeRef.current = Date.now();
    } catch (err) {
      setSetupError(
        extractApiErrorMessage(
          err,
          'Failed to start diagnostic assessment. Ensure Ollama is running or topics exist.'
        )
      );
    } finally {
      setIsStarting(false);
    }
  };

  // Submit Completed Assessment
  const handleFinalSubmit = async () => {
    if (!sessionData || !courseId) return;

    recordQuestionTime();
    setIsSubmitting(true);

    try {
      const submissions = sessionData.questions.map((q) => ({
        question_id: q.id,
        selected_answer: answers[q.id] || '',
        time_taken: timePerQuestion[q.id] || 0,
      }));

      const result = await submitDiagnostic(sessionData.session_id, submissions);
      setIsSubmitModalOpen(false);
      navigate(`/courses/${courseId}/diagnostic/${result.session_id}/result`);
    } catch (err) {
      alert(extractApiErrorMessage(err, 'Failed to submit diagnostic assessment.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  // ---------------------------------------------------------------------------
  // View 1: Loading & Setup Errors
  // ---------------------------------------------------------------------------
  if (isLoadingSetup) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <h2 className="text-xl font-bold text-slate-800">Preparing Diagnostic Assessment...</h2>
        <p className="text-sm text-slate-500 mt-1">Loading topics and course configuration</p>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // View 2: Active Diagnostic Quiz Taking Mode
  // ---------------------------------------------------------------------------
  if (sessionData && sessionData.questions.length > 0) {
    const currentQ = sessionData.questions[currentQuestionIndex];
    const totalQ = sessionData.questions.length;
    const answeredCount = Object.keys(answers).length;
    const answeredIndices = new Set(
      sessionData.questions
        .map((q, idx) => (answers[q.id] ? idx : -1))
        .filter((idx) => idx !== -1)
    );

    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Header Bar */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 sm:p-6 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Diagnostic Assessment In Progress
                </span>
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900 mt-1">
                {course?.title || 'Diagnostic Assessment'}
              </h1>
            </div>

            <div className="flex items-center space-x-4">
              <AssessmentTimer />
              <button
                type="button"
                onClick={() => setIsSubmitModalOpen(true)}
                className="px-4 py-2 text-xs sm:text-sm font-semibold rounded-xl bg-slate-900 hover:bg-slate-800 text-white shadow-sm transition-colors"
              >
                End & Submit
              </button>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-100">
            <AssessmentProgress answeredCount={answeredCount} totalCount={totalQ} />
          </div>
        </div>

        {/* Question Area */}
        <div className="space-y-6">
          {currentQ && (
            <QuestionCard
              question={currentQ}
              questionIndex={currentQuestionIndex}
              totalQuestions={totalQ}
              selectedAnswer={answers[currentQ.id] || ''}
              onSelectAnswer={handleSelectAnswer}
            />
          )}

          {/* Navigation Controls */}
          <QuestionNavigation
            totalQuestions={totalQ}
            currentIndex={currentQuestionIndex}
            answeredIndices={answeredIndices}
            onSelectIndex={handleNavigateIndex}
            onPrevious={handlePrevious}
            onNext={handleNext}
            onSubmit={() => setIsSubmitModalOpen(true)}
          />
        </div>

        {/* Final Submission Confirmation Modal */}
        <SubmitConfirmationModal
          isOpen={isSubmitModalOpen}
          totalQuestions={totalQ}
          answeredCount={answeredCount}
          isSubmitting={isSubmitting}
          onConfirm={handleFinalSubmit}
          onCancel={() => setIsSubmitModalOpen(false)}
        />
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // View 3: Assessment Configuration & Start Screen
  // ---------------------------------------------------------------------------
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link
          to={`/courses/${courseId}`}
          className="inline-flex items-center text-sm font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" />
          Back to {course?.title || 'Course Details'}
        </Link>
      </div>

      {/* Hero Banner */}
      <div className="bg-gradient-to-br from-indigo-900 via-indigo-800 to-slate-900 rounded-3xl p-6 sm:p-10 text-white shadow-xl mb-8 relative overflow-hidden">
        <div className="relative z-10">
          <div className="inline-flex items-center space-x-2 px-3 py-1 bg-indigo-500/30 rounded-full border border-indigo-400/30 text-xs font-semibold uppercase tracking-wider text-indigo-200 mb-4">
            <Sparkles className="w-3.5 h-3.5 text-indigo-300" />
            <span>AI Knowledge Diagnostic</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight">
            Diagnostic Assessment
          </h1>
          <p className="text-indigo-100/90 text-sm sm:text-base max-w-2xl mt-3 leading-relaxed">
            Evaluate your foundational topic knowledge across this course. Our diagnostic engine
            generates targeted conceptual questions from your syllabus to pinpoint your strengths
            and weak areas.
          </p>
        </div>
      </div>

      {setupError && (
        <div className="mb-6 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start space-x-3">
          <HelpCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Unable to Start Diagnostic</p>
            <p className="mt-0.5">{setupError}</p>
          </div>
        </div>
      )}

      {availableTopics.length === 0 ? (
        <div className="bg-white rounded-3xl border border-slate-200 p-8 text-center shadow-sm">
          <div className="w-16 h-16 bg-amber-100 text-amber-700 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <BrainCircuit className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-slate-900">No Extracted Topics Found</h3>
          <p className="text-slate-600 text-sm max-w-md mx-auto mt-2 mb-6">
            You must extract syllabus topics before launching a diagnostic assessment.
          </p>
          <Link
            to={`/courses/${courseId}/topics`}
            className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold shadow-sm transition-colors"
          >
            <span>Go to Topics & Extract</span>
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-8">
          {/* Assessment Mode Selector */}
          <div>
            <label className="block text-sm font-bold text-slate-900 mb-3">
              Assessment Scope
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setMode('full')}
                className={`p-5 rounded-2xl border-2 text-left transition-all ${
                  mode === 'full'
                    ? 'border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-500/20'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-slate-900">Full Course Diagnostic</span>
                  {mode === 'full' && <CheckCircle2 className="w-5 h-5 text-indigo-600" />}
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Evaluates all core units and topics across the entire syllabus for a complete baseline.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setMode('selected')}
                className={`p-5 rounded-2xl border-2 text-left transition-all ${
                  mode === 'selected'
                    ? 'border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-500/20'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-slate-900">Custom Topic Selection</span>
                  {mode === 'selected' && <CheckCircle2 className="w-5 h-5 text-indigo-600" />}
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Choose specific topics you want to test right now for targeted knowledge evaluation.
                </p>
              </button>
            </div>
          </div>

          {/* Topic Checkboxes (shown when mode === 'selected') */}
          {mode === 'selected' && (
            <div className="pt-2 border-t border-slate-100">
              <div className="flex items-center justify-between mb-3">
                <label className="text-sm font-bold text-slate-900">
                  Select Topics ({selectedTopicIds.length} of {availableTopics.length} selected)
                </label>
                <div className="space-x-3 text-xs">
                  <button
                    type="button"
                    onClick={handleSelectAllTopics}
                    className="text-indigo-600 hover:text-indigo-800 font-medium"
                  >
                    Select All
                  </button>
                  <button
                    type="button"
                    onClick={handleClearAllTopics}
                    className="text-slate-500 hover:text-slate-700 font-medium"
                  >
                    Clear All
                  </button>
                </div>
              </div>

              <div className="max-h-64 overflow-y-auto space-y-2 p-3 bg-slate-50 rounded-2xl border border-slate-200">
                {availableTopics.map((topic) => {
                  const isChecked = selectedTopicIds.includes(topic.id);
                  return (
                    <label
                      key={topic.id}
                      className="flex items-center space-x-3 p-2.5 rounded-xl hover:bg-white transition-colors cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleToggleTopic(topic.id)}
                        className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300"
                      />
                      <div className="flex-1 text-sm font-medium text-slate-800">
                        {topic.name}
                        {topic.unit_name && (
                          <span className="ml-2 text-xs text-slate-500 font-normal">
                            ({topic.unit_name})
                          </span>
                        )}
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          {/* Difficulty & Questions Per Topic Settings */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2 border-t border-slate-100">
            <div>
              <label className="block text-sm font-bold text-slate-900 mb-2">
                Question Difficulty
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as any)}
                className="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm font-medium text-slate-800 bg-white"
              >
                <option value="mixed">Mixed (Recommended - Balanced)</option>
                <option value="easy">Easy (Foundational)</option>
                <option value="medium">Medium (Analytical)</option>
                <option value="hard">Hard (Advanced Problem Solving)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-900 mb-2">
                Questions Per Topic
              </label>
              <select
                value={questionsPerTopic}
                onChange={(e) => setQuestionsPerTopic(Number(e.target.value))}
                className="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm font-medium text-slate-800 bg-white"
              >
                <option value={1}>1 Question per topic (Quick check)</option>
                <option value={2}>2 Questions per topic (Standard)</option>
                <option value={3}>3 Questions per topic (Comprehensive)</option>
                <option value={5}>5 Questions per topic (Deep diagnostic)</option>
              </select>
            </div>
          </div>

          {/* Action CTA */}
          <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Estimated duration:{' '}
              {Math.max(
                3,
                (mode === 'selected' ? selectedTopicIds.length : availableTopics.length) *
                  questionsPerTopic *
                  1.5
              )}{' '}
              minutes
            </span>

            <button
              type="button"
              onClick={handleStartAssessment}
              disabled={isStarting}
              className="inline-flex items-center space-x-2 px-8 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm shadow-md hover:shadow-lg transition-all disabled:opacity-50"
            >
              {isStarting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Generating Questions...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Start Assessment</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
