import React from 'react';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

interface SubmitConfirmationModalProps {
  isOpen: boolean;
  totalQuestions: number;
  answeredCount: number;
  isSubmitting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const SubmitConfirmationModal: React.FC<SubmitConfirmationModalProps> = ({
  isOpen,
  totalQuestions,
  answeredCount,
  isSubmitting,
  onConfirm,
  onCancel,
}) => {
  if (!isOpen) return null;

  const unansweredCount = totalQuestions - answeredCount;
  const hasUnanswered = unansweredCount > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-100">
        <div className="flex items-center space-x-3 mb-4">
          <div
            className={`w-12 h-12 rounded-xl flex items-center justify-center ${
              hasUnanswered ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'
            }`}
          >
            {hasUnanswered ? (
              <AlertCircle className="w-6 h-6" />
            ) : (
              <CheckCircle2 className="w-6 h-6" />
            )}
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">
              {hasUnanswered ? 'Unanswered Questions' : 'Ready to Submit?'}
            </h3>
            <p className="text-xs text-slate-500">Diagnostic Assessment Evaluation</p>
          </div>
        </div>

        <div className="bg-slate-50 rounded-xl p-4 mb-6 border border-slate-200">
          <div className="flex justify-between items-center text-sm py-1">
            <span className="text-slate-600">Total Questions:</span>
            <span className="font-semibold text-slate-800">{totalQuestions}</span>
          </div>
          <div className="flex justify-between items-center text-sm py-1">
            <span className="text-slate-600">Answered:</span>
            <span className="font-semibold text-emerald-700">{answeredCount}</span>
          </div>
          {hasUnanswered && (
            <div className="flex justify-between items-center text-sm py-1 border-t border-slate-200 mt-1 pt-1">
              <span className="text-amber-700 font-medium">Unanswered:</span>
              <span className="font-bold text-amber-700">{unansweredCount}</span>
            </div>
          )}
        </div>

        {hasUnanswered && (
          <p className="text-sm text-amber-800 bg-amber-50 rounded-lg p-3 border border-amber-200 mb-6">
            You still have <strong>{unansweredCount}</strong> unanswered question(s). Unanswered
            questions will be scored as 0%.
          </p>
        )}

        <div className="flex items-center justify-end space-x-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-xl transition-colors border border-slate-300"
          >
            Review Questions
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isSubmitting}
            className="px-5 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm transition-colors disabled:opacity-50 flex items-center space-x-2"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Evaluating...</span>
              </>
            ) : (
              <span>Submit Now</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

