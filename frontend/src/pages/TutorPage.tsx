import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import {
  Bot,
  BookOpen,
  ArrowLeft,
  Loader2,
  AlertCircle,
  CheckCircle,
  HelpCircle,
  TrendingUp,
  RotateCcw,
  Sparkles,
  ExternalLink,
  Info,
} from 'lucide-react';
import {
  Course,
  ExplanationLevel,
  PracticeEvaluationResult,
  PracticeQuestion,
  TeachingStage,
  Topic,
  TopicDetail,
  TutorLanguage,
  TutorMessage,
  TutorSessionDetail,
  UnitGroup,
} from '../types';
import { getCourses } from '../services/courseService';
import { getCourseTopics, getTopicById } from '../services/topicService';
import {
  completeTutorSession,
  generatePracticeQuestion,
  getTutorSession,
  requestHint,
  sendTutorMessage,
  startTutorSession,
  submitPracticeAnswer,
  updateTutorPreferences,
} from '../services/tutorService';
import {
  TeachingProgress,
  TutorPreferences,
  TutorChat,
  PracticeCard,
} from '../components/tutor';

export const TutorPage: React.FC = () => {
  const { courseId: paramCourseId, topicId: paramTopicId } = useParams<{
    courseId?: string;
    topicId?: string;
  }>();
  const [searchParams] = useSearchParams();
  const planItemId = searchParams.get('plan_item_id');
  const queryCourseId = searchParams.get('course_id');
  const queryTopicId = searchParams.get('topic_id');

  // Selection state when navigated to /tutor directly
  const [courses, setCourses] = useState<Course[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>(
    paramCourseId || queryCourseId || ''
  );
  const [selectedTopicId, setSelectedTopicId] = useState<string>(
    paramTopicId || queryTopicId || ''
  );
  const [topicDetail, setTopicDetail] = useState<TopicDetail | null>(null);

  // Active Session state
  const [session, setSession] = useState<TutorSessionDetail | null>(null);
  const [messages, setMessages] = useState<TutorMessage[]>([]);
  const [suggestedAction, setSuggestedAction] = useState<string>('');
  const [activeQuestion, setActiveQuestion] = useState<PracticeQuestion | null>(null);

  // UI state
  const [isLoadingSession, setIsLoadingSession] = useState<boolean>(false);
  const [isSendingMessage, setIsSendingMessage] = useState<boolean>(false);
  const [isGeneratingPractice, setIsGeneratingPractice] = useState<boolean>(false);
  const [isCompletingSession, setIsCompletingSession] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Preferences
  const [language, setLanguage] = useState<TutorLanguage>('english');
  const [explanationLevel, setExplanationLevel] = useState<ExplanationLevel>('intermediate');

  // Load user courses on mount
  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const res = await getCourses();
        setCourses(res.data.courses);
        if (!selectedCourseId && res.data.courses.length > 0) {
          setSelectedCourseId(res.data.courses[0].id);
        }
      } catch (err: unknown) {
        console.error('Failed to load courses', err);
      }
    };
    fetchCourses();
  }, [selectedCourseId]);

  // Load topics when course changes
  useEffect(() => {
    if (!selectedCourseId) {
      setTopics([]);
      return;
    }
    const fetchTopics = async () => {
      try {
        const res = await getCourseTopics(selectedCourseId);
        const allTopics: Topic[] = [];
        res.data.units.forEach((u: UnitGroup) => {
          allTopics.push(...u.topics);
        });
        setTopics(allTopics);
        if (!selectedTopicId && allTopics.length > 0) {
          setSelectedTopicId(allTopics[0].id);
        }
      } catch (err: unknown) {
        console.error('Failed to load topics', err);
      }
    };
    fetchTopics();
  }, [selectedCourseId, selectedTopicId]);

  // Load topic detail for sidebar
  useEffect(() => {
    if (!selectedTopicId) {
      setTopicDetail(null);
      return;
    }
    const fetchTopicDetail = async () => {
      try {
        const res = await getTopicById(selectedTopicId);
        setTopicDetail(res.data);
      } catch {
        // Fallback or ignore
      }
    };
    fetchTopicDetail();
  }, [selectedTopicId]);

  // Start or Initialize Tutor Session
  const handleStartSession = useCallback(async () => {
    if (!selectedCourseId || !selectedTopicId) return;

    try {
      setIsLoadingSession(true);
      setErrorMessage(null);
      setSuccessBanner(null);

      const sessionData = await startTutorSession(selectedCourseId, {
        topic_id: selectedTopicId,
        plan_item_id: planItemId,
        language,
        explanation_level: explanationLevel,
      });

      setSession(sessionData);
      setMessages(sessionData.recent_messages || []);
      setLanguage(sessionData.language);
      setExplanationLevel(sessionData.explanation_level);
      setSuggestedAction(sessionData.session_metadata?.suggested_next_action || '');
      setActiveQuestion(null);
    } catch (err: unknown) {
      console.error('Failed to initialize tutor session', err);
      setErrorMessage('Could not initialize tutor session. Please verify your connection.');
    } finally {
      setIsLoadingSession(false);
    }
  }, [selectedCourseId, selectedTopicId, planItemId, language, explanationLevel]);

  // Automatically initialize session if URL params exist
  useEffect(() => {
    const effectiveCourseId = paramCourseId || queryCourseId;
    const effectiveTopicId = paramTopicId || queryTopicId;
    if (effectiveCourseId && effectiveTopicId && !session && !isLoadingSession) {
      setSelectedCourseId(effectiveCourseId);
      setSelectedTopicId(effectiveTopicId);
      handleStartSession();
    }
  }, [
    paramCourseId,
    paramTopicId,
    queryCourseId,
    queryTopicId,
    session,
    isLoadingSession,
    handleStartSession,
  ]);

  // Handle student message
  const handleSendMessage = async (content: string) => {
    if (!session || isSendingMessage) return;

    try {
      setIsSendingMessage(true);
      setErrorMessage(null);

      // Optimistic user message
      const tempUserMsg: TutorMessage = {
        id: `client-${Date.now()}`,
        session_id: session.id,
        role: 'user',
        content,
        message_type: 'text',
        related_topic_id: session.topic_id,
        sources: [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, tempUserMsg]);

      const resp = await sendTutorMessage(session.id, content);

      // Append assistant reply
      setMessages((prev) => [...prev, resp.message]);
      setSuggestedAction(resp.suggested_next_action || '');

      // Update session stage
      setSession((prev) =>
        prev
          ? {
              ...prev,
              current_stage: resp.current_stage,
            }
          : null
      );

      // If transition entered PRACTICE, automatically trigger question generation
      if (resp.current_stage === 'PRACTICE' && !activeQuestion) {
        handleGeneratePractice();
      }
    } catch (err: unknown) {
      console.error('Failed to send tutor message', err);
      setErrorMessage('Failed to send message. Please retry.');
    } finally {
      setIsSendingMessage(false);
    }
  };

  // Handle stage change from stepper
  const handleSelectStage = async (stage: TeachingStage) => {
    if (!session) return;
    try {
      const updated = await updateTutorPreferences(session.id, {
        current_stage: stage,
      });
      setSession(updated);

      if (stage === 'PRACTICE' && !activeQuestion) {
        handleGeneratePractice();
      }
    } catch (err: unknown) {
      console.error('Failed to switch stage', err);
    }
  };

  // Handle preferences update
  const handleChangePreferences = async (prefs: {
    language?: TutorLanguage;
    explanation_level?: ExplanationLevel;
  }) => {
    if (prefs.language) setLanguage(prefs.language);
    if (prefs.explanation_level) setExplanationLevel(prefs.explanation_level);

    if (session) {
      try {
        const updated = await updateTutorPreferences(session.id, prefs);
        setSession(updated);
      } catch (err: unknown) {
        console.error('Failed to update preferences', err);
      }
    }
  };

  // Generate Practice Question
  const handleGeneratePractice = async (difficulty?: string) => {
    if (!session || isGeneratingPractice) return;

    try {
      setIsGeneratingPractice(true);
      setErrorMessage(null);
      const question = await generatePracticeQuestion(session.id, difficulty);
      setActiveQuestion(question);

      // Also append a system notice in chat
      const practiceNotice: TutorMessage = {
        id: `notice-${Date.now()}`,
        session_id: session.id,
        role: 'assistant',
        content: `I've prepared a targeted practice problem for **${session.topic_name}** to verify your understanding. Solve the problem below to earn topic mastery credit!`,
        message_type: 'practice_question',
        related_topic_id: session.topic_id,
        sources: [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, practiceNotice]);
    } catch (err: unknown) {
      console.error('Failed to generate practice question', err);
      setErrorMessage('Could not generate practice problem right now.');
    } finally {
      setIsGeneratingPractice(false);
    }
  };

  // Submit Practice Answer
  const handleSubmitAnswer = async (
    questionId: string,
    answer: string
  ): Promise<PracticeEvaluationResult & { correct_answer?: string; explanation?: string }> => {
    if (!session) throw new Error('No active session');

    const result = await submitPracticeAnswer(session.id, questionId, answer);

    // Refresh session to get updated metadata and scores
    try {
      const refreshedSession = await getTutorSession(session.id);
      setSession(refreshedSession);
    } catch {
      // ignore
    }

    // Add evaluation message into dialogue
    const evalMessage: TutorMessage = {
      id: `eval-${Date.now()}`,
      session_id: session.id,
      role: 'assistant',
      content: result.is_correct
        ? `✅ **Correct!** (${Math.round(result.score * 100)}% accuracy)\n\n${result.feedback}\n\n*Topic Mastery updated!*`
        : `⚠️ **Needs Revision**\n\n${result.feedback}\n\n**Advice:** ${result.next_step_advice}`,
      message_type: 'evaluation',
      related_topic_id: session.topic_id,
      sources: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, evalMessage]);

    return result;
  };

  // Request Socratic Hint
  const handleRequestHint = async (questionId: string, hintLevel: number) => {
    if (!session) throw new Error('No active session');
    const hintData = await requestHint(session.id, questionId, hintLevel);

    // Also echo hint in chat stream
    const hintMsg: TutorMessage = {
      id: `hint-${Date.now()}`,
      session_id: session.id,
      role: 'assistant',
      content: `💡 **Socratic Hint ${hintData.hint_level}**: ${hintData.hint}`,
      message_type: 'hint',
      related_topic_id: session.topic_id,
      sources: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, hintMsg]);

    return hintData;
  };

  // Complete Session
  const handleCompleteSession = async () => {
    if (!session || isCompletingSession) return;

    try {
      setIsCompletingSession(true);
      const finished = await completeTutorSession(session.id);
      setSession(finished);
      setSuccessBanner(
        'Congratulations! Tutoring session completed and topic mastery evidence recorded.'
      );
    } catch (err: unknown) {
      console.error('Failed to complete session', err);
      setErrorMessage('Could not finalize session.');
    } finally {
      setIsCompletingSession(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Header & Breadcrumbs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-gray-200 shadow-2xs">
        <div className="space-y-1">
          <div className="flex items-center space-x-2 text-xs text-gray-500 font-medium">
            <Link
              to={selectedCourseId ? `/courses/${selectedCourseId}` : '/courses'}
              className="hover:text-indigo-600 transition-colors flex items-center space-x-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Course</span>
            </Link>
            <span>/</span>
            <span>AI Tutor</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center space-x-2">
            <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Bot className="w-5 h-5" />
            </div>
            <span>
              {session ? session.topic_name : '1-on-1 Personalized AI Tutor'}
            </span>
          </h1>
          <p className="text-xs text-gray-500">
            Socratic concept mastery grounded in your uploaded syllabus materials.
          </p>
        </div>

        {/* Course & Topic Selection Pickers */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedCourseId}
            onChange={(e) => setSelectedCourseId(e.target.value)}
            disabled={isLoadingSession || isSendingMessage}
            className="rounded-xl border border-gray-300 bg-white px-3 py-2 text-xs font-medium text-gray-700 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
          >
            <option value="" disabled>
              Select Course...
            </option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>

          <select
            value={selectedTopicId}
            onChange={(e) => setSelectedTopicId(e.target.value)}
            disabled={isLoadingSession || isSendingMessage || topics.length === 0}
            className="rounded-xl border border-gray-300 bg-white px-3 py-2 text-xs font-medium text-gray-700 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
          >
            <option value="" disabled>
              Select Topic...
            </option>
            {topics.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.difficulty})
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={handleStartSession}
            disabled={
              !selectedCourseId || !selectedTopicId || isLoadingSession || isSendingMessage
            }
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-xs"
          >
            {isLoadingSession ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Initializing...</span>
              </>
            ) : session ? (
              <>
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Restart Session</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Start Tutoring</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Alerts */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-500" />
          <span>{errorMessage}</span>
        </div>
      )}

      {successBanner && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center space-x-2">
          <CheckCircle className="w-4 h-4 flex-shrink-0 text-emerald-600" />
          <span>{successBanner}</span>
        </div>
      )}

      {/* Main Tutor Area */}
      {session ? (
        <div className="space-y-6">
          {/* Teaching State Machine Progress Bar */}
          <TeachingProgress
            currentStage={session.current_stage}
            onSelectStage={handleSelectStage}
          />

          {/* 3-Column / Responsive Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Left Column: Topic & Prerequisite Knowledge Context */}
            <div className="lg:col-span-1 space-y-4">
              {/* Topic Information Card */}
              <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-2xs space-y-3">
                <div className="flex items-center justify-between border-b border-gray-100 pb-2">
                  <div className="flex items-center space-x-1.5 font-semibold text-sm text-gray-900">
                    <BookOpen className="w-4 h-4 text-indigo-600" />
                    <span>Topic Context</span>
                  </div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700">
                    {session.status}
                  </span>
                </div>

                <div className="space-y-1">
                  <h3 className="text-base font-bold text-gray-900">
                    {session.topic_name}
                  </h3>
                  {topicDetail?.unit_name && (
                    <p className="text-xs text-gray-500 font-medium">
                      {topicDetail.unit_name}
                    </p>
                  )}
                  {topicDetail?.description && (
                    <p className="text-xs text-gray-600 leading-relaxed pt-1">
                      {topicDetail.description}
                    </p>
                  )}
                </div>

                {/* Prerequisites Trace */}
                {topicDetail?.prerequisites && topicDetail.prerequisites.length > 0 && (
                  <div className="pt-2 border-t border-gray-100 space-y-1.5">
                    <span className="text-xs font-semibold text-gray-700 flex items-center space-x-1">
                      <TrendingUp className="w-3.5 h-3.5 text-gray-400" />
                      <span>Foundational Prerequisites</span>
                    </span>
                    <div className="space-y-1">
                      {topicDetail.prerequisites.map((p) => (
                        <div
                          key={p.id}
                          className="flex items-center justify-between p-2 rounded-lg bg-gray-50 border border-gray-200 text-xs text-gray-700"
                        >
                          <span className="font-medium truncate max-w-[140px]">
                            {p.name}
                          </span>
                          <span className="text-[10px] font-mono text-gray-400">
                            {Math.round(p.confidence * 100)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Socratic Pedagogy Guidelines Pill */}
              <div className="bg-indigo-50/50 rounded-xl border border-indigo-100 p-4 text-xs text-indigo-900 space-y-2">
                <div className="flex items-center space-x-1.5 font-semibold text-indigo-800">
                  <Info className="w-4 h-4 text-indigo-600" />
                  <span>How CoursePilot Teaches</span>
                </div>
                <ul className="list-disc list-inside space-y-1 text-indigo-700 text-[11px] leading-relaxed">
                  <li>Asks diagnostic questions to check prerequisite grasp</li>
                  <li>Avoids giving direct answers immediately</li>
                  <li>Provides progressive hints and dry-run code traces</li>
                  <li>Updates your mastery evidence through practice</li>
                </ul>
              </div>
            </div>

            {/* Center Column: Tutor Dialogue & Interactive Practice */}
            <div className="lg:col-span-2 space-y-4">
              {/* Active Practice Question Card if in PRACTICE stage or generated */}
              {activeQuestion && (
                <PracticeCard
                  question={activeQuestion}
                  onSubmitAnswer={handleSubmitAnswer}
                  onRequestHint={handleRequestHint}
                  onNextQuestion={() => handleGeneratePractice(activeQuestion.difficulty)}
                  onContinueChat={() => setActiveQuestion(null)}
                />
              )}

              {/* Chat Stream */}
              <TutorChat
                messages={messages}
                onSendMessage={handleSendMessage}
                suggestedAction={suggestedAction}
                isSending={isSendingMessage}
              />
            </div>

            {/* Right Column: Personalization & Session Actions */}
            <div className="lg:col-span-1 space-y-4">
              {/* Tutor Preferences Panel */}
              <TutorPreferences
                language={language}
                explanationLevel={explanationLevel}
                onChangePreferences={handleChangePreferences}
                disabled={isSendingMessage}
              />

              {/* Quick Actions Panel */}
              <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-2xs space-y-3">
                <span className="text-xs font-semibold text-gray-700 flex items-center space-x-1">
                  <HelpCircle className="w-3.5 h-3.5 text-gray-400" />
                  <span>Practice & Verification</span>
                </span>

                <button
                  type="button"
                  onClick={() => handleGeneratePractice('medium')}
                  disabled={isGeneratingPractice || isSendingMessage}
                  className="w-full inline-flex items-center justify-center space-x-1.5 py-2.5 px-3 rounded-xl text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors"
                >
                  {isGeneratingPractice ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5" />
                  )}
                  <span>Generate Practice Question</span>
                </button>

                <button
                  type="button"
                  onClick={handleCompleteSession}
                  disabled={isCompletingSession || session.status === 'completed'}
                  className="w-full inline-flex items-center justify-center space-x-1.5 py-2.5 px-3 rounded-xl text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 transition-colors disabled:opacity-50"
                >
                  {isCompletingSession ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <CheckCircle className="w-3.5 h-3.5" />
                  )}
                  <span>
                    {session.status === 'completed'
                      ? 'Session Completed'
                      : 'Mark Topic Mastered'}
                  </span>
                </button>

                {session.plan_item_id && (
                  <Link
                    to={`/courses/${selectedCourseId}/study-plan`}
                    className="w-full inline-flex items-center justify-center space-x-1 py-2 text-xs font-medium text-gray-500 hover:text-indigo-600 transition-colors"
                  >
                    <span>Return to Study Plan</span>
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Empty State when no session is active */
        <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center shadow-xs">
          <div className="w-16 h-16 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto mb-4">
            <Bot className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-gray-900">
            Select a Course & Topic to Begin Tutoring
          </h2>
          <p className="mt-2 text-sm text-gray-500 max-w-md mx-auto leading-relaxed">
            Choose any topic from your uploaded syllabus above. CoursePilot AI will trace your prerequisite gaps, adapt explanations to your preferred language, and generate grounded practice problems.
          </p>
          <div className="mt-6 flex justify-center">
            <button
              type="button"
              onClick={handleStartSession}
              disabled={!selectedCourseId || !selectedTopicId || isLoadingSession}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-xs"
            >
              {isLoadingSession ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Setting up session...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Launch 1-on-1 Session</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
