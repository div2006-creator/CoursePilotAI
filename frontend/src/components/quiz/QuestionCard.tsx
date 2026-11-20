import React from 'react';
import { QuestionPublic } from '../../types';

interface QuestionCardProps {
  question: QuestionPublic;
  questionIndex: number;
  totalQuestions: number;
  selectedAnswer: string;
  onSelectAnswer: (answer: string) => void;
}

export const QuestionCard: React.FC<QuestionCardProps> = ({
  question,
  questionIndex,
  totalQuestions,
  selectedAnswer,
  onSelectAnswer,
}) => {
  const optionLetters = ['A', 'B', 'C', 'D'];

  const getDifficultyBadge = (diff: string) => {
    switch (diff.toLowerCase()) {
      case 'easy':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'medium':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'hard':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-300';
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8">
      {/* Question Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6 pb-4 border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-semibold px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
            Question {questionIndex + 1} of {totalQuestions}
          </span>
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
            {question.topic_name}
          </span>
        </div>
        <span
          className={`text-xs font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-md border ${getDifficultyBadge(
            question.difficulty
          )}`}
        >
          {question.difficulty}
        </span>
      </div>

      {/* Question Prompt */}
      <div className="mb-8">
        <h3 className="text-lg sm:text-xl font-medium text-slate-900 leading-relaxed">
          {question.question}
        </h3>
      </div>

      {/* 4 Options */}
      <div className="space-y-3">
        {question.options.map((option, idx) => {
          const letter = optionLetters[idx] || `${idx + 1}`;
          const isSelected = selectedAnswer === option;

          return (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectAnswer(option)}
              className={`w-full flex items-start text-left p-4 rounded-xl border-2 transition-all duration-150 ${
                isSelected
                  ? 'border-indigo-600 bg-indigo-50/70 shadow-sm ring-2 ring-indigo-500/20'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/80 bg-white'
              }`}
            >
              <div
                className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm mr-4 transition-colors ${
                  isSelected
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-100 text-slate-700 border border-slate-200'
                }`}
              >
                {letter}
              </div>
              <div className="flex-1 pt-1 text-slate-800 font-normal leading-normal">
                {option}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

