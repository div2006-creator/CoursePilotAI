import React, { useEffect, useState } from 'react';
import { AlertCircle, Layers, Loader2, X } from 'lucide-react';
import { Topic, TopicDetail, TopicUpdatePayload } from '../../types';
import { extractApiErrorMessage } from '../../services/api';

interface EditTopicModalProps {
  isOpen: boolean;
  topic: Topic | TopicDetail | null;
  onClose: () => void;
  onSubmit: (payload: TopicUpdatePayload) => Promise<void>;
}

interface FormErrors {
  name?: string;
  unit_name?: string;
}

export const EditTopicModal: React.FC<EditTopicModalProps> = ({
  isOpen,
  topic,
  onClose,
  onSubmit,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [difficulty, setDifficulty] = useState('medium');
  const [unitName, setUnitName] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isOpen || !topic) {
      return;
    }
    setName(topic.name);
    setDescription(topic.description || '');
    setDifficulty(topic.difficulty || 'medium');
    setUnitName(topic.unit_name || '');
    setErrors({});
    setServerError(null);
  }, [isOpen, topic]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isSubmitting) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isSubmitting, onClose]);

  if (!isOpen || !topic) {
    return null;
  }

  const validate = (): boolean => {
    const nextErrors: FormErrors = {};
    const trimmedName = name.trim();
    if (!trimmedName) {
      nextErrors.name = 'Topic name is required.';
    } else if (trimmedName.length > 255) {
      nextErrors.name = 'Topic name cannot exceed 255 characters.';
    }

    if (unitName.trim().length > 100) {
      nextErrors.unit_name = 'Unit name cannot exceed 100 characters.';
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);

    if (!validate()) {
      return;
    }

    const payload: TopicUpdatePayload = {
      name: name.trim(),
      description: description.trim() ? description.trim() : null,
      difficulty,
      unit_name: unitName.trim() ? unitName.trim() : null,
    };

    setIsSubmitting(true);
    try {
      await onSubmit(payload);
      onClose();
    } catch (err) {
      setServerError(
        extractApiErrorMessage(err, 'Failed to update topic. Please try again.')
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
      aria-labelledby="edit-topic-modal-title"
    >
      <div className="w-full max-w-lg rounded-xl bg-white shadow-xl border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h2 id="edit-topic-modal-title" className="text-base font-semibold text-gray-900">
                Edit Topic
              </h2>
              <p className="text-xs text-gray-500">Update academic concept details or unit grouping</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 disabled:opacity-50 transition-colors"
          >
            <X className="w-4 h-4" />
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
            <label htmlFor="topic-name" className="block text-sm font-medium text-gray-700 mb-1">
              Topic Name <span className="text-red-500">*</span>
            </label>
            <input
              id="topic-name"
              type="text"
              required
              maxLength={255}
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (errors.name) setErrors((prev) => ({ ...prev, name: undefined }));
              }}
              className={`w-full rounded-lg border px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                errors.name ? 'border-red-300' : 'border-gray-300'
              }`}
            />
            {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name}</p>}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="topic-unit" className="block text-sm font-medium text-gray-700 mb-1">
                Unit / Module Name
              </label>
              <input
                id="topic-unit"
                type="text"
                maxLength={100}
                value={unitName}
                onChange={(e) => {
                  setUnitName(e.target.value);
                  if (errors.unit_name) setErrors((prev) => ({ ...prev, unit_name: undefined }));
                }}
                placeholder="e.g. Unit 1: Linear Structures"
                className={`w-full rounded-lg border px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                  errors.unit_name ? 'border-red-300' : 'border-gray-300'
                }`}
              />
              {errors.unit_name && <p className="mt-1 text-xs text-red-600">{errors.unit_name}</p>}
            </div>

            <div>
              <label htmlFor="topic-difficulty" className="block text-sm font-medium text-gray-700 mb-1">
                Difficulty Level
              </label>
              <select
                id="topic-difficulty"
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="easy">Easy (Foundational)</option>
                <option value="medium">Medium (Intermediate)</option>
                <option value="hard">Hard (Advanced)</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="topic-description" className="block text-sm font-medium text-gray-700 mb-1">
              Description <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <textarea
              id="topic-description"
              rows={3}
              maxLength={5000}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Academic concept scope, learning outcomes, or syllabus details..."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

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
              <span>{isSubmitting ? 'Saving...' : 'Save Changes'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EditTopicModal;

