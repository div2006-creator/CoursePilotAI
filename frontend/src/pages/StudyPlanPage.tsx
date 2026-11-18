import React from 'react';
import { CalendarCheck } from 'lucide-react';

export const StudyPlanPage: React.FC = () => {
  return (
    <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 text-center">
      <div className="mx-auto w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center mb-4">
        <CalendarCheck className="w-6 h-6" />
      </div>
      <h1 className="text-2xl font-bold text-gray-900">Personalized Study Plan (Placeholder)</h1>
      <p className="mt-2 text-sm text-gray-500 max-w-md mx-auto">
        Dynamic recovery schedule resolving prerequisite gaps before upcoming exam deadlines.
      </p>
    </div>
  );
};

