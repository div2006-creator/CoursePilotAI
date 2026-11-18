import React from 'react';
import { BarChart3 } from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  return (
    <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 text-center">
      <div className="mx-auto w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center mb-4">
        <BarChart3 className="w-6 h-6" />
      </div>
      <h1 className="text-2xl font-bold text-gray-900">Mastery & Progress Analytics (Placeholder)</h1>
      <p className="mt-2 text-sm text-gray-500 max-w-md mx-auto">
        Interactive mastery charts and knowledge retention diagnostics powered by Recharts.
      </p>
    </div>
  );
};

