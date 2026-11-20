import React, { useEffect, useState } from 'react';
import { AlertCircle, AlertTriangle, Calendar, Clock, Loader2, X } from 'lucide-react';
import { Course, CourseCreatePayload, CourseUpdatePayload } from '../../types';
import { extractApiErrorMessage } from '../../services/api';
import { formatStudyMinutes, isPastDateString } from '../../utils/courseFormatters';

interface CourseFormModalProps {
  isOpen: boolean;
  mode: 'create' | 'edit';
  initialCourse?: Course | null;
  onClose: () => void;
  onSubmit: (payload: CourseCreatePayload | CourseUpdatePayload) => Promise<void>;
}

interface FormErrors {
  title?: string;
  description?: string;
  exam_date?: string;
  daily_minutes?: string;
}

const DAILY_PRESETS = [30, 60, 90, 120, 180];

export const CourseFormModal: React.FC<CourseFormModalProps> = ({
  isOpen,
  mode,
  initialCourse,
  onClose,
  onSubmit,
}) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [examDate, setExamDate] = useState('');
  const [dailyMinutes, setDailyMinutes] = useState('60');
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    if (mode === 'edit' && initialCourse) {
      setTitle(initialCourse.title);
      setDescription(initialCourse.description ?? '');
      setExamDate(initialCourse.exam_date ?? '');
      setDailyMinutes(String(initialCourse.daily_minutes));
    } else {
      setTitle('');
      setDescription('');
      setExamDate('');
      setDailyMinutes('60');
    }
    setErrors({});
    setServerError(null);
  }, [isOpen, mode, initialCourse]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isSubmitting) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isSubmitting, onClose]);

  if (!isOpen) {
    return null;
  }

  const parsedMinutes = Number(dailyMinutes);
  const showPastDateWarning = Boolean(examDate && isPastDateString(examDate));

  const validate = (): boolean => {
    const nextErrors: FormErrors = {};
    const trimmedTitle = title.trim();

    if (!trimmedTitle) {
      nextErrors.title = 'Course title is required.';
    } else if (trimmedTitle.length < 2) {
      nextErrors.title = 'Course title must be at least 2 characters.';
    } else if (trimmedTitle.length > 100) {
      nextErrors.title = 'Course title must be 100 characters or fewer.';
    }

    if (description.trim().length > 2000) {
      nextErrors.description = 'Description must be 2,000 characters or fewer.';
    }

    if (
      !dailyMinutes.trim() ||
      Number.isNaN(parsedMinutes) ||
      !Number.isInteger(parsedMinutes)
    ) {
      nextErrors.daily_minutes = 'Please enter a whole number of minutes.';
    } else if (parsedMinutes < 15 || parsedMinutes > 720) {
      nextErrors.daily_minutes = 'Daily study time must be between 15 and 720 minutes.';
    }

    if (examDate && !/^\d{4}-\d{2}-\d{2}$/.test(examDate)) {
      nextErrors.exam_date = 'Please choose a valid exam date.';
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setServerError(null);

    if (!validate()) {
      return;
    }

    const payload: CourseCreatePayload = {
      title: title.trim(),
      description: description.trim() ? description.trim() : null,
      exam_date: examDate ? examDate : null,
      daily_minutes: parsedMinutes,
    };

    setIsSubmitting(true);
    try {
      await onSubmit(payload);
    } catch (error) {
      setServerError(
        extractApiErrorMessage(
          error,
          mode === 'create'
            ? 'Failed to create course. Please try again.'
            : 'Failed to update course. Please try again.'
        )
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 px-4 py-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="course-modal-title"
    >
      <div className="w-full max-w-lg rounded-xl bg-white shadow-xl border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 id="course-modal-title" className="text-lg font-semibold text-gray-900">
              {mode === 'create' ? 'Create New Course' : 'Edit Course'}
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              {mode === 'create'
                ? 'Set up a subject, target exam date, and daily study budget.'
                : 'Update your course details, exam date, or daily availability.'}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            aria-label="Close modal"
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 disabled:opacity-50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate className="p-6 space-y-4">
          {serverError && (
            <div
              role="alert"
              className="flex items-start space-x-2.5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
            >
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{serverError}</span>
            </div>
          )}

          <div>
            <label
              htmlFor="course-title"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Course title <span className="text-red-500">*</span>
            </label>
            <input
              id="course-title"
              name="title"
              type="text"
              required
              maxLength={100}
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                if (errors.title) setErrors((prev) => ({ ...prev, title: undefined }));
              }}
              placeholder="e.g. Data Structures and Algorithms"
              className={`w-full rounded-lg border px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                errors.title ? 'border-red-300' : 'border-gray-300'
              }`}
            />
            <div className="mt-1 flex justify-between">
              {errors.title ? (
                <p className="text-xs text-red-600">{errors.title}</p>
              ) : (
                <span className="text-xs text-gray-400">2–100 characters</span>
              )}
              <span className="text-xs text-gray-400">{title.trim().length}/100</span>
            </div>
          </div>

          <div>
            <label
              htmlFor="course-description"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Description <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <textarea
              id="course-description"
              name="description"
              rows={3}
              maxLength={2000}
              value={description}
              onChange={(e) => {
                setDescription(e.target.value);
                if (errors.description) {
                  setErrors((prev) => ({ ...prev, description: undefined }));
                }
              }}
              placeholder="Key chapters, syllabus goals, or areas you want to strengthen..."
              className={`w-full rounded-lg border px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                errors.description ? 'border-red-300' : 'border-gray-300'
              }`}
            />
            {errors.description && (
              <p className="mt-1 text-xs text-red-600">{errors.description}</p>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="course-exam-date"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                <span className="inline-flex items-center space-x-1">
                  <Calendar className="w-3.5 h-3.5 text-gray-400" />
                  <span>Exam date</span>
                  <span className="text-gray-400 font-normal">(optional)</span>
                </span>
              </label>
              <input
                id="course-exam-date"
                name="exam_date"
                type="date"
                value={examDate}
                onChange={(e) => {
                  setExamDate(e.target.value);
                  if (errors.exam_date) {
                    setErrors((prev) => ({ ...prev, exam_date: undefined }));
                  }
                }}
                className={`w-full rounded-lg border px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                  errors.exam_date ? 'border-red-300' : 'border-gray-300'
                }`}
              />
              {errors.exam_date && (
                <p className="mt-1 text-xs text-red-600">{errors.exam_date}</p>
              )}
            </div>

            <div>
              <label
                htmlFor="course-daily-minutes"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                <span className="inline-flex items-center space-x-1">
                  <Clock className="w-3.5 h-3.5 text-gray-400" />
                  <span>Daily study time (min)</span>
                  <span className="text-red-500">*</span>
                </span>
              </label>
              <input
                id="course-daily-minutes"
                name="daily_minutes"
                type="number"
                min={15}
                max={720}
                step={5}
                required
                value={dailyMinutes}
                onChange={(e) => {
                  setDailyMinutes(e.target.value);
                  if (errors.daily_minutes) {
                    setErrors((prev) => ({ ...prev, daily_minutes: undefined }));
                  }
                }}
                className={`w-full rounded-lg border px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                  errors.daily_minutes ? 'border-red-300' : 'border-gray-300'
                }`}
              />
              {errors.daily_minutes ? (
                <p className="mt-1 text-xs text-red-600">{errors.daily_minutes}</p>
              ) : (
                <p className="mt-1 text-xs text-gray-400">
                  15–720 min
                  {!Number.isNaN(parsedMinutes) && parsedMinutes >= 15 && parsedMinutes <= 720
                    ? ` (${formatStudyMinutes(parsedMinutes)}/day)`
                    : ''}
                </p>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-gray-500 mr-1">Quick select:</span>
            {DAILY_PRESETS.map((preset) => (
              <button
                key={preset}
                type="button"
                onClick={() => {
                  setDailyMinutes(String(preset));
                  if (errors.daily_minutes) {
                    setErrors((prev) => ({ ...prev, daily_minutes: undefined }));
                  }
                }}
                className={`px-2.5 py-1 rounded-md text-xs font-medium border transition-colors ${
                  parsedMinutes === preset
                    ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                    : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
                }`}
              >
                {formatStudyMinutes(preset)}
              </button>
            ))}
          </div>

          {showPastDateWarning && (
            <div className="flex items-start space-x-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
              <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-600" />
              <span>
                The selected exam date is in the past. You can still save it, and the course will
                be marked as <strong>Exam Passed</strong>.
              </span>
            </div>
          )}

          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-gray-100">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-60 transition-colors"
            >
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>
                {isSubmitting
                  ? mode === 'create'
                    ? 'Creating...'
                    : 'Saving...'
                  : mode === 'create'
                    ? 'Create Course'
                    : 'Save Changes'}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

