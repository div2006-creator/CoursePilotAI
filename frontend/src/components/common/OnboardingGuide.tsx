import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CheckCircle2,
  ArrowRight,
  Sparkles,
  BookOpen,
  FileText,
  Layers,
  Award,
  Calendar,
  BrainCircuit,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Course } from '../../types';

interface OnboardingGuideProps {
  courses: Course[];
  hasDocuments?: boolean;
  hasTopics?: boolean;
  hasDiagnostics?: boolean;
  hasStudyPlan?: boolean;
  hasTutorSession?: boolean;
}

export const OnboardingGuide: React.FC<OnboardingGuideProps> = ({
  courses,
  hasDocuments = false,
  hasTopics = false,
  hasDiagnostics = false,
  hasStudyPlan = false,
  hasTutorSession = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  const hasCourse = courses.length > 0;
  const activeCourseId = hasCourse ? courses[0].id : null;

  const steps = [
    {
      num: 1,
      title: 'Create Your Course',
      desc: 'Set up your course title, target exam date, and daily study availability.',
      isDone: hasCourse,
      to: '/courses',
      ctaText: 'Create Course',
      icon: BookOpen,
    },
    {
      num: 2,
      title: 'Upload Syllabus (PDF)',
      desc: 'Upload your syllabus or lecture slides to extract units and page references.',
      isDone: hasDocuments,
      to: activeCourseId ? `/courses/${activeCourseId}` : '/courses',
      ctaText: 'Upload PDF',
      icon: FileText,
    },
    {
      num: 3,
      title: 'Review Topics & Graph',
      desc: 'AI parses units, subtopics, and prerequisite dependencies into a DAG.',
      isDone: hasTopics,
      to: activeCourseId ? `/courses/${activeCourseId}/topics` : '/courses',
      ctaText: 'View Topics',
      icon: Layers,
    },
    {
      num: 4,
      title: 'Take Diagnostic Quiz',
      desc: 'Discover your strengths, developing concepts, and prerequisite knowledge gaps.',
      isDone: hasDiagnostics,
      to: activeCourseId ? `/courses/${activeCourseId}/diagnostic` : '/courses',
      ctaText: 'Start Quiz',
      icon: Award,
    },
    {
      num: 5,
      title: 'Generate Study Plan',
      desc: 'Get an adaptive roadmap prioritizing foundational gaps before exam deadlines.',
      isDone: hasStudyPlan,
      to: activeCourseId ? `/courses/${activeCourseId}/study-plan` : '/study-plan',
      ctaText: 'View Roadmap',
      icon: Calendar,
    },
    {
      num: 6,
      title: 'AI Tutor Session',
      desc: '1-on-1 Socratic concept recovery with examples, progressive hints, and practice.',
      isDone: hasTutorSession,
      to: activeCourseId ? `/courses/${activeCourseId}/tutor` : '/tutor',
      ctaText: 'Start Tutoring',
      icon: BrainCircuit,
    },
  ];

  const completedCount = steps.filter((s) => s.isDone).length;
  const progressPct = Math.round((completedCount / steps.length) * 100);

  return (
    <div className="bg-gradient-to-r from-indigo-900 via-indigo-800 to-indigo-900 rounded-2xl p-6 text-white shadow-md space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 bg-white/10 rounded-lg text-amber-300">
              <Sparkles className="w-4 h-4" />
            </span>
            <h2 className="text-lg font-bold">Your Learning Journey Guide</h2>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-700/80 text-indigo-100 font-semibold border border-indigo-600">
              {completedCount} of 6 Completed ({progressPct}%)
            </span>
          </div>
          <p className="text-xs text-indigo-200 mt-1">
            Follow the 6 core steps to diagnose knowledge gaps, follow your personalized roadmap, and master concepts with your AI Tutor.
          </p>
        </div>

        <button
          onClick={() => setIsExpanded((prev) => !prev)}
          className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 transition-colors flex items-center gap-1.5 self-start sm:self-center"
        >
          <span>{isExpanded ? 'Collapse Guide' : 'Expand Steps'}</span>
          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-indigo-950/60 rounded-full h-2 overflow-hidden">
        <div
          className="bg-gradient-to-r from-amber-400 to-emerald-400 h-2 rounded-full transition-all duration-500"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Expanded Steps Grid */}
      {isExpanded && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
          {steps.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.num}
                className={`p-3.5 rounded-xl border transition-all flex flex-col justify-between space-y-3 ${
                  step.isDone
                    ? 'bg-white/10 border-emerald-400/30'
                    : 'bg-white/5 border-white/10 hover:bg-white/10'
                }`}
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold ${
                          step.isDone
                            ? 'bg-emerald-400 text-indigo-950'
                            : 'bg-white/20 text-white'
                        }`}
                      >
                        {step.num}
                      </span>
                      <Icon className="w-4 h-4 text-indigo-300" />
                    </div>
                    {step.isDone ? (
                      <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-300">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Done
                      </span>
                    ) : (
                      <span className="text-[11px] font-medium text-amber-300">Next Up</span>
                    )}
                  </div>
                  <h4 className="text-xs font-bold text-white">{step.title}</h4>
                  <p className="text-[11px] text-indigo-200 line-clamp-2">{step.desc}</p>
                </div>

                <Link
                  to={step.to}
                  className={`inline-flex items-center justify-between px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    step.isDone
                      ? 'bg-white/10 text-indigo-200 hover:bg-white/20'
                      : 'bg-amber-400 hover:bg-amber-300 text-indigo-950 shadow-sm'
                  }`}
                >
                  <span>{step.isDone ? 'Review' : step.ctaText}</span>
                  <ArrowRight className="w-3 h-3 ml-1" />
                </Link>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default OnboardingGuide;
