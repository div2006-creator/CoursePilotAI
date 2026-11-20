import React, { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';

interface AssessmentTimerProps {
  onTick?: (seconds: number) => void;
  isRunning?: boolean;
}

export const AssessmentTimer: React.FC<AssessmentTimerProps> = ({
  onTick,
  isRunning = true,
}) => {
  const [secondsElapsed, setSecondsElapsed] = useState(0);

  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(() => {
      setSecondsElapsed((prev) => {
        const next = prev + 1;
        if (onTick) onTick(next);
        return next;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isRunning, onTick]);

  const formatTime = (totalSecs: number) => {
    const mins = Math.floor(totalSecs / 60);
    const secs = totalSecs % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex items-center space-x-2 px-3.5 py-1.5 bg-slate-100/80 rounded-xl border border-slate-200 text-slate-700 text-sm font-medium">
      <Clock className="w-4 h-4 text-indigo-600 animate-pulse" />
      <span>{formatTime(secondsElapsed)}</span>
    </div>
  );
};

