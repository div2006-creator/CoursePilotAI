import React, { useState } from 'react';
import {
  HelpCircle,
  Lightbulb,
  Send,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Loader2,
  TrendingUp,
  AlertCircle,
  Sparkles,
} from 'lucide-react';
import {
  HintData,
  PracticeEvaluationResult,
  PracticeQuestion,
} from '../../types';

interface PracticeCardProps {
  question: PracticeQuestion;
  onSubmitAnswer: (
    questionId: string,
    answer: string
  ) => Promise<PracticeEvaluationResult & { correct_answer?: string; explanation?: string }>;
  onRequestHint: (questionId: string, hintLevel: number) => Promise<HintData>;
  onNextQuestion?: () => void;
  onContinueChat?: () => void;
  disabled?: boolean;
}

export const PracticeCard: React.FC<PracticeCardProps> = ({
  question,
  onSubmitAnswer,
  onRequestHint,
  onNextQuestion,
  onContinueChat,
  disabled = false,
}) => {
  const [selectedOption, setSelectedOption] = useState<string>('');
  const [freeTextAnswer, setFreeTextAnswer] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hints, setHints] = useState<HintData[]>([]);
  const [isLoadingHint, setIsLoadingHint] = useState(false);
  const [evaluation, setEvaluation] = useState<
    (PracticeEvaluationResult & { correct_answer?: string; explanation?: string }) | null
  >(null);

  const hasOptions = question.options && question.options.length > 0;
  const currentAnswer = hasOptions ? selectedOption : freeTextAnswer;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentAnswer.trim() || isSubmitting || disabled) return;

    try {
      setIsSubmitting(true);
      const result = await onSubmitAnswer(question.id, currentAnswer.trim());
      setEvaluation(result);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRequestHint = async () => {
    if (isLoadingHint || disabled) return;
    const nextLevel = hints.length + 1;
    if (nextLevel > 3) return;

    try {
      setIsLoadingHint(true);
      const hintData = await onRequestHint(question.id, nextLevel);
      setHints((prev) => [...prev, hintData]);
    } finally {
      setIsLoadingHint(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border-2 border-indigo-200/80 shadow-md p-5 space-y-4">
      {/* Question Header */}
      <div className="flex items-center justify-between border-b border-gray-100 pb-3">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
            <HelpCircle className="w-4 h-4" />
          </div>
          <div>
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Practice Problem • {question.topic_name}
            </span>
            <span className="ml-2 text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
              {question.difficulty.toUpperCase()}
            </span>
          </div>
        </div>
      </div>

      {/* Question Body */}
      <div className="text-gray-900 font-medium text-base whitespace-pre-wrap leading-relaxed">
        {question.question}
      </div>

      {/* Answer Form */}
      {!evaluation && (
        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          {hasOptions ? (
            <div className="space-y-2">
              {question.options.map((option, idx) => {
                const isSelected = selectedOption === option;
                return (
                  <button
                    key={idx}
                    type="button"
                    disabled={disabled || isSubmitting}
                    onClick={() => setSelectedOption(option)}
                    className={`w-full text-left p-3 rounded-xl border text-sm font-medium transition-all flex items-center space-x-3 ${
                      isSelected
                        ? 'border-indigo-600 bg-indigo-50/60 text-indigo-900 shadow-2xs ring-1 ring-indigo-500'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-gray-800'
                    }`}
                  >
                    <span
                      className={`w-6 h-6 rounded-full border flex items-center justify-center text-xs font-semibold ${
                        isSelected
                          ? 'border-indigo-600 bg-indigo-600 text-white'
                          : 'border-gray-300 text-gray-500'
                      }`}
                    >
                      {String.fromCharCode(65 + idx)}
                    </span>
                    <span className="flex-1">{option}</span>
                  </button>
                );
              })}
            </div>
          ) : (
            <div>
              <textarea
                value={freeTextAnswer}
                onChange={(e) => setFreeTextAnswer(e.target.value)}
                placeholder="Write your explanation or code trace here..."
                rows={4}
                disabled={disabled || isSubmitting}
                className="w-full rounded-xl border border-gray-300 p-3 text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono"
              />
            </div>
          )}

          {/* Socratic Progressive Hints */}
          {hints.length > 0 && (
            <div className="space-y-2 pt-2">
              {hints.map((h, i) => (
                <div
                  key={i}
                  className="p-3 rounded-xl bg-amber-50/80 border border-amber-200 text-xs text-amber-900 space-y-1"
                >
                  <div className="flex items-center space-x-1 font-semibold text-amber-800">
                    <Lightbulb className="w-3.5 h-3.5" />
                    <span>Hint {h.hint_level}</span>
                    <span className="text-[10px] text-amber-600 ml-1 font-normal">
                      ({h.instruction})
                    </span>
                  </div>
                  <p className="leading-relaxed">{h.hint}</p>
                </div>
              ))}
            </div>
          )}

          {/* Controls: Hints & Submit */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              disabled={isLoadingHint || hints.length >= 3 || isSubmitting || disabled}
              onClick={handleRequestHint}
              className="inline-flex items-center space-x-1.5 text-xs font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >
              {isLoadingHint ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Lightbulb className="w-3.5 h-3.5" />
              )}
              <span>
                {hints.length === 0
                  ? 'Ask for Socratic Hint'
                  : hints.length < 3
                  ? `Next Hint (${hints.length}/3)`
                  : 'All Hints Unlocked'}
              </span>
            </button>

            <button
              type="submit"
              disabled={!currentAnswer.trim() || isSubmitting || disabled}
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-xs"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Evaluating...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>Submit Answer</span>
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* Structured Evaluation Result */}
      {evaluation && (
        <div className="pt-2 space-y-4">
          <div
            className={`p-4 rounded-xl border ${
              evaluation.is_correct
                ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                : 'bg-rose-50 border-rose-200 text-rose-900'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                {evaluation.is_correct ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-600" />
                )}
                <span className="font-bold text-sm">
                  {evaluation.is_correct
                    ? 'Excellent! Correct Solution'
                    : 'Needs Revision'}
                </span>
              </div>
              <div className="flex items-center space-x-1 font-mono text-xs font-semibold px-2.5 py-1 rounded-full bg-white/80 shadow-2xs">
                <TrendingUp className="w-3.5 h-3.5 text-indigo-600" />
                <span>Score: {Math.round(evaluation.score * 100)}%</span>
              </div>
            </div>

            <p className="text-sm leading-relaxed mb-3">{evaluation.feedback}</p>

            {/* Strengths & Errors Breakdown */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              {evaluation.strengths && evaluation.strengths.length > 0 && (
                <div className="bg-white/70 p-2.5 rounded-lg border border-emerald-100">
                  <div className="font-semibold text-emerald-800 mb-1 flex items-center space-x-1">
                    <Sparkles className="w-3 h-3" />
                    <span>Strengths</span>
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-emerald-700">
                    {evaluation.strengths.map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {evaluation.errors_identified && evaluation.errors_identified.length > 0 && (
                <div className="bg-white/70 p-2.5 rounded-lg border border-rose-100">
                  <div className="font-semibold text-rose-800 mb-1 flex items-center space-x-1">
                    <AlertCircle className="w-3 h-3" />
                    <span>Areas to Improve</span>
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-rose-700">
                    {evaluation.errors_identified.map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Next Step Advice */}
            {evaluation.next_step_advice && (
              <div className="mt-3 text-xs bg-white/80 p-2.5 rounded-lg border border-gray-200">
                <span className="font-semibold text-gray-800">
                  Recommended Action:{' '}
                </span>
                <span className="text-gray-600">{evaluation.next_step_advice}</span>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end space-x-3 pt-1">
            {onNextQuestion && (
              <button
                type="button"
                onClick={onNextQuestion}
                className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors"
              >
                <span>Try Another Problem</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {onContinueChat && (
              <button
                type="button"
                onClick={onContinueChat}
                className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-xs"
              >
                <span>Discuss with Tutor</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

