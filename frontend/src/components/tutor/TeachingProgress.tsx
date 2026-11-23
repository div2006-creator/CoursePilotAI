import React from 'react';
import {
  Stethoscope,
  BookOpen,
  Code2,
  Dumbbell,
  CheckCircle2,
  Trophy,
} from 'lucide-react';
import { TeachingStage } from '../../types';

interface TeachingProgressProps {
  currentStage: TeachingStage;
  onSelectStage?: (stage: TeachingStage) => void;
}

interface StageStep {
  stage: TeachingStage;
  label: string;
  shortDesc: string;
  icon: React.ComponentType<{ className?: string }>;
}

const STAGES: StageStep[] = [
  {
    stage: 'DIAGNOSIS',
    label: 'Diagnosis',
    shortDesc: 'Knowledge Check',
    icon: Stethoscope,
  },
  {
    stage: 'EXPLANATION',
    label: 'Explanation',
    shortDesc: 'Concept Deep Dive',
    icon: BookOpen,
  },
  {
    stage: 'EXAMPLE',
    label: 'Example',
    shortDesc: 'Dry Run & Trace',
    icon: Code2,
  },
  {
    stage: 'PRACTICE',
    label: 'Practice',
    shortDesc: 'Targeted Problem',
    icon: Dumbbell,
  },
  {
    stage: 'VERIFICATION',
    label: 'Verification',
    shortDesc: 'Confirm Mastery',
    icon: CheckCircle2,
  },
  {
    stage: 'COMPLETED',
    label: 'Completed',
    shortDesc: 'Topic Mastered',
    icon: Trophy,
  },
];

export const TeachingProgress: React.FC<TeachingProgressProps> = ({
  currentStage,
  onSelectStage,
}) => {
  const currentIndex = STAGES.findIndex((s) => s.stage === currentStage);
  const activeIndex = currentIndex === -1 ? 0 : currentIndex;
  const progressPercent = Math.round((activeIndex / (STAGES.length - 1)) * 100);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-2xs">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
            Stage {activeIndex + 1} of {STAGES.length}
          </span>
          <span className="text-sm font-bold text-gray-900">
            {STAGES[activeIndex]?.label}: {STAGES[activeIndex]?.shortDesc}
          </span>
        </div>
        <span className="text-xs font-semibold text-gray-500 font-mono">
          {progressPercent}% Complete
        </span>
      </div>

      {/* Progress Bar Track */}
      <div className="w-full bg-gray-100 h-2 rounded-full overflow-hidden mb-4">
        <div
          className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Stepper Buttons */}
      <div className="grid grid-cols-6 gap-1 sm:gap-2">
        {STAGES.map((step, idx) => {
          const Icon = step.icon;
          const isPassed = idx < activeIndex;
          const isCurrent = idx === activeIndex;

          return (
            <button
              key={step.stage}
              type="button"
              onClick={() => onSelectStage && onSelectStage(step.stage)}
              className={`flex flex-col items-center p-2 rounded-lg text-center transition-all duration-150 ${
                isCurrent
                  ? 'bg-indigo-50 text-indigo-700 ring-2 ring-indigo-500/50 shadow-xs'
                  : isPassed
                  ? 'text-emerald-700 hover:bg-emerald-50/50'
                  : 'text-gray-400 hover:bg-gray-50'
              }`}
              title={`${step.label}: ${step.shortDesc}`}
            >
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center mb-1 text-xs font-medium ${
                  isCurrent
                    ? 'bg-indigo-600 text-white'
                    : isPassed
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'bg-gray-100 text-gray-400'
                }`}
              >
                {isPassed ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : (
                  <Icon className="w-3.5 h-3.5" />
                )}
              </div>
              <span className="text-[11px] font-medium truncate max-w-full hidden sm:block">
                {step.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

