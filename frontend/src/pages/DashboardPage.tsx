import React, { useEffect, useState } from 'react';
import { checkHealth } from '../services/api';
import { HealthStatus } from '../types';
import { CheckCircle2, AlertCircle } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    checkHealth()
      .then((data) => setHealth(data))
      .catch((err) => setError(err.message || 'Unable to connect to backend'));
  }, []);

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard (Placeholder)</h1>
        <p className="mt-2 text-sm text-gray-500">
          CoursePilot AI personalized learning recovery dashboard. Full UI components to be implemented in subsequent phases.
        </p>
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Backend Integration Status</h2>
        {health ? (
          <div className="flex items-center space-x-3 text-emerald-700 bg-emerald-50 p-4 rounded-lg border border-emerald-200">
            <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            <div className="text-sm">
              <span className="font-semibold">Backend Connected:</span> {health.app_name} (v{health.version}) &bull; Status: <span className="uppercase">{health.status}</span>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center space-x-3 text-amber-700 bg-amber-50 p-4 rounded-lg border border-amber-200">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <div className="text-sm">
              <span className="font-semibold">Backend Status:</span> {error} (Ensure backend server is running on port 8000)
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500">Checking API status...</p>
        )}
      </div>
    </div>
  );
};

