import React from 'react';

interface AssessmentProgressProps {
  answeredCount: number;
  totalCount: number;
}

export const AssessmentProgress: React.FC<AssessmentProgressProps> = ({
  answeredCount,
  totalCount,
}) => {
  const percentage = totalCount > 0 ? Math.round((answeredCount / totalCount) * 100) : 0;

  return (
    <div className="w-full">
      <div className="flex justify-between items-center text-xs font-semibold text-slate-600 mb-1.5">
        <span>
          {answeredCount} of {totalCount} Answered
        </span>
        <span>{percentage}%</span>
      </div>
      <div className="w-full h-2.5 bg-slate-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-600 rounded-full transition-all duration-300 ease-out"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

