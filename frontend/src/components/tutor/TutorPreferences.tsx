import React from 'react';
import { Languages, Gauge, Sparkles } from 'lucide-react';
import { ExplanationLevel, TutorLanguage } from '../../types';

interface TutorPreferencesProps {
  language: TutorLanguage;
  explanationLevel: ExplanationLevel;
  onChangePreferences: (prefs: {
    language?: TutorLanguage;
    explanation_level?: ExplanationLevel;
  }) => void;
  disabled?: boolean;
}

export const TutorPreferences: React.FC<TutorPreferencesProps> = ({
  language,
  explanationLevel,
  onChangePreferences,
  disabled = false,
}) => {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-2xs space-y-4">
      <div className="flex items-center space-x-2 text-gray-800 font-semibold text-sm border-b border-gray-100 pb-2">
        <Sparkles className="w-4 h-4 text-indigo-600" />
        <span>Tutor Personalization</span>
      </div>

      {/* Language Selector */}
      <div className="space-y-1.5">
        <label className="flex items-center text-xs font-medium text-gray-600">
          <Languages className="w-3.5 h-3.5 mr-1 text-gray-400" />
          <span>Explanation Language</span>
        </label>
        <div className="grid grid-cols-3 gap-1.5">
          {(
            [
              { id: 'english', label: 'English', desc: 'Standard' },
              { id: 'hinglish', label: 'Hinglish', desc: 'Bilingual' },
              { id: 'hindi', label: 'हिंदी', desc: 'Hindi' },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              type="button"
              disabled={disabled}
              onClick={() => onChangePreferences({ language: item.id })}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium text-center border transition-all ${
                language === item.id
                  ? 'bg-indigo-50 border-indigo-300 text-indigo-700 shadow-2xs'
                  : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              <div className="font-semibold">{item.label}</div>
              <div className="text-[10px] text-gray-400">{item.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Explanation Level Selector */}
      <div className="space-y-1.5">
        <label className="flex items-center text-xs font-medium text-gray-600">
          <Gauge className="w-3.5 h-3.5 mr-1 text-gray-400" />
          <span>Conceptual Depth</span>
        </label>
        <div className="grid grid-cols-3 gap-1.5">
          {(
            [
              { id: 'beginner', label: 'Beginner', desc: 'Step-by-step' },
              { id: 'intermediate', label: 'College', desc: 'Standard' },
              { id: 'advanced', label: 'Advanced', desc: 'Proof & Invariant' },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              type="button"
              disabled={disabled}
              onClick={() => onChangePreferences({ explanation_level: item.id })}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium text-center border transition-all ${
                explanationLevel === item.id
                  ? 'bg-indigo-50 border-indigo-300 text-indigo-700 shadow-2xs'
                  : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              <div className="font-semibold">{item.label}</div>
              <div className="text-[10px] text-gray-400">{item.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

