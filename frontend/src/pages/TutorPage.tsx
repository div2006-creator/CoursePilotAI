import React from 'react';
import { BotMessageSquare } from 'lucide-react';

export const TutorPage: React.FC = () => {
  return (
    <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 text-center">
      <div className="mx-auto w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center mb-4">
        <BotMessageSquare className="w-6 h-6" />
      </div>
      <h1 className="text-2xl font-bold text-gray-900">AI Tutor (Placeholder)</h1>
      <p className="mt-2 text-sm text-gray-500 max-w-md mx-auto">
        RAG-powered conversational tutoring grounded in your uploaded DSA lecture notes and syllabus material.
      </p>
    </div>
  );
};

