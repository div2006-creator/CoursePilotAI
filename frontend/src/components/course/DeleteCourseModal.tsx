import React, { useEffect, useState } from 'react';
import { AlertCircle, AlertTriangle, Loader2, Trash2, X } from 'lucide-react';
import { Course } from '../../types';
import { extractApiErrorMessage } from '../../services/api';

interface DeleteCourseModalProps {
  course: Course | null;
  onClose: () => void;
  onConfirm: (course: Course) => Promise<void>;
}

export const DeleteCourseModal: React.FC<DeleteCourseModalProps> = ({
  course,
  onClose,
  onConfirm,
}) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!course) {
      return;
    }
    setErrorMessage(null);
    setIsDeleting(false);
  }, [course]);

  useEffect(() => {
    if (!course) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isDeleting) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [course, isDeleting, onClose]);

  if (!course) {
    return null;
  }

  const handleConfirm = async () => {
    setErrorMessage(null);
    setIsDeleting(true);
    try {
      await onConfirm(course);
    } catch (error) {
      setErrorMessage(
        extractApiErrorMessage(error, 'Failed to delete course. Please try again.')
      );
      setIsDeleting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 px-4 py-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-course-modal-title"
    >
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl border border-gray-200 overflow-hidden">
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-red-50 text-red-600 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h2
                id="delete-course-modal-title"
                className="text-base font-semibold text-gray-900"
              >
                Delete Course
              </h2>
              <p className="text-xs text-gray-500">This action cannot be undone.</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isDeleting}
            aria-label="Close delete confirmation"
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 disabled:opacity-50 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {errorMessage && (
            <div
              role="alert"
              className="flex items-start space-x-2.5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
            >
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <p className="text-sm text-gray-600 leading-relaxed">
            Are you sure you want to permanently delete{' '}
            <span className="font-semibold text-gray-900">&ldquo;{course.title}&rdquo;</span>?
            All course configuration and any associated learning data will be removed.
          </p>

          <div className="flex items-center justify-end space-x-3 pt-2 border-t border-gray-100">
            <button
              type="button"
              onClick={onClose}
              disabled={isDeleting}
              className="px-4 py-2 rounded-lg text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={isDeleting}
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-60 transition-colors"
            >
              {isDeleting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4" />
              )}
              <span>{isDeleting ? 'Deleting...' : 'Delete Course'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

