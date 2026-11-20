import React from 'react';
import { ChevronLeft, ChevronRight, Check } from 'lucide-react';

interface QuestionNavigationProps {
  totalQuestions: number;
  currentIndex: number;
  answeredIndices: Set<number>;
  onSelectIndex: (index: number) => void;
  onPrevious: () => void;
  onNext: () => void;
  onSubmit: () => void;
}

export const QuestionNavigation: React.FC<QuestionNavigationProps> = ({
  totalQuestions,
  currentIndex,
  answeredIndices,
  onSelectIndex,
  onPrevious,
  onNext,
  onSubmit,
}) => {
  const isFirst = currentIndex === 0;
  const isLast = currentIndex === totalQuestions - 1;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
      <h4 className="text-sm font-semibold text-slate-800 mb-4">Question Palette</h4>

      {/* Grid of question number buttons */}
      <div className="grid grid-cols-5 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-2 mb-6">
        {Array.from({ length: totalQuestions }).map((_, idx) => {
          const isCurrent = idx === currentIndex;
          const isAnswered = answeredIndices.has(idx);

          let buttonStyle = 'bg-slate-100 text-slate-700 hover:bg-slate-200 border-slate-200';
          if (isCurrent) {
            buttonStyle = 'bg-indigo-600 text-white font-bold ring-2 ring-indigo-500 ring-offset-2';
          } else if (isAnswered) {
            buttonStyle = 'bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold';
          }

          return (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectIndex(idx)}
              className={`h-9 rounded-lg border text-xs flex items-center justify-center transition-all ${buttonStyle}`}
              aria-label={`Go to question ${idx + 1}`}
            >
              {isAnswered && !isCurrent ? (
                <span className="flex items-center space-x-0.5">
                  <span>{idx + 1}</span>
                  <Check className="w-3 h-3 text-emerald-600" />
                </span>
              ) : (
                idx + 1
              )}
            </button>
          );
        })}
      </div>

      {/* Prev / Next / Submit Action Bar */}
      <div className="flex items-center justify-between pt-4 border-t border-slate-100">
        <button
          type="button"
          onClick={onPrevious}
          disabled={isFirst}
          className={`flex items-center space-x-1.5 px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${
            isFirst
              ? 'border-slate-200 text-slate-400 cursor-not-allowed bg-slate-50'
              : 'border-slate-300 text-slate-700 hover:bg-slate-50'
          }`}
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Previous</span>
        </button>

        {isLast ? (
          <button
            type="button"
            onClick={onSubmit}
            className="flex items-center space-x-1.5 px-6 py-2.5 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-colors"
          >
            <span>Finish & Submit</span>
            <Check className="w-4 h-4" />
          </button>
        ) : (
          <button
            type="button"
            onClick={onNext}
            className="flex items-center space-x-1.5 px-5 py-2 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-colors"
          >
            <span>Next</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};

