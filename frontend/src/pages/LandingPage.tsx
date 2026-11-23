import React from 'react';
import { Link } from 'react-router-dom';
import {
  Compass,
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  ShieldCheck,
  TrendingUp,
  Award,
  Sparkles,
  GitFork,
  FileText,
  Check,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const LandingPage: React.FC = () => {
  const { isAuthenticated, user } = useAuth();

  return (
    <div className="min-h-screen bg-white text-gray-900 selection:bg-indigo-500 selection:text-white">
      {/* Navigation Bar */}
      <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md">
              <Compass className="w-6 h-6" />
            </div>
            <div>
              <span className="font-bold text-xl text-gray-900 tracking-tight">CoursePilot</span>
              <span className="text-xs font-semibold text-indigo-600 ml-1.5 uppercase px-2 py-0.5 bg-indigo-50 rounded-full border border-indigo-100">
                AI
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center space-x-6 text-sm font-medium text-gray-600">
            <a href="#problem" className="hover:text-indigo-600 transition-colors">The Problem</a>
            <a href="#how-it-works" className="hover:text-indigo-600 transition-colors">How It Works</a>
            <a href="#workflow" className="hover:text-indigo-600 transition-colors">6-Stage Recovery</a>
            <a href="#tutor" className="hover:text-indigo-600 transition-colors">AI Tutor</a>
            <a href="#comparison" className="hover:text-indigo-600 transition-colors">Why CoursePilot</a>
          </nav>

          <div className="flex items-center space-x-3">
            {isAuthenticated ? (
              <Link
                to="/dashboard"
                className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm transition-all"
              >
                <span>Dashboard ({user?.name.split(' ')[0]})</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            ) : (
              <>
                <Link
                  to="/login"
                  className="px-4 py-2 text-sm font-semibold text-gray-700 hover:text-gray-900 transition-colors"
                >
                  Log In
                </Link>
                <Link
                  to="/register"
                  className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm transition-all hover:shadow"
                >
                  <span>Start Learning Free</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* SECTION 1: HERO */}
      <section className="relative overflow-hidden pt-16 pb-20 lg:pt-24 lg:pb-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-indigo-50 border border-indigo-100 text-xs font-semibold text-indigo-700 mb-6">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>Homingo Hackathon 2026 &bull; Track C3: A Tutor for Every Learner</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-black text-gray-900 tracking-tight leading-tight max-w-4xl mx-auto">
            Your AI tutor that <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-indigo-700 to-purple-600">doesn&apos;t stop until you understand.</span>
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto font-normal leading-relaxed">
            From knowledge gaps to real understanding. CoursePilot diagnoses what you don&apos;t know, teaches what you&apos;re missing, and verifies what you&apos;ve learned.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to={isAuthenticated ? "/dashboard" : "/register"}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-7 py-3.5 rounded-xl text-base font-bold text-white bg-indigo-600 hover:bg-indigo-700 shadow-lg shadow-indigo-600/20 transition-all hover:scale-102"
            >
              <span>{isAuthenticated ? "Open Workspace" : "Get Started — It's Free"}</span>
              <ArrowRight className="w-5 h-5" />
            </Link>
            <a
              href="#how-it-works"
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-7 py-3.5 rounded-xl text-base font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 transition-all"
            >
              <span>See Demo Flow</span>
            </a>
          </div>

          {/* Value Props Pills */}
          <div className="mt-12 pt-8 border-t border-gray-100 flex flex-wrap items-center justify-center gap-6 sm:gap-10 text-xs font-semibold text-gray-500 uppercase tracking-wider">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>Grounded in Your Syllabus</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>Prerequisite DAG Intelligence</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>English &bull; Hindi &bull; Hinglish</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>Verified Fresh Assessments</span>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 2: THE PROBLEM */}
      <section id="problem" className="py-16 bg-gray-50 border-y border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <h2 className="text-xs font-bold uppercase tracking-wider text-rose-600">The Problem</h2>
            <p className="mt-2 text-3xl font-extrabold text-gray-900 tracking-tight">
              Students don&apos;t fail because of a lack of material. They fail because they study blindly.
            </p>
            <p className="mt-4 text-base text-gray-600 leading-relaxed">
              When a computer science student struggles with Dynamic Programming, they typically grind 20 more DP problems and fail again. Why? Because the actual blocker is an unmastered foundational concept: <strong>Recursion state trees and base cases</strong>.
            </p>
          </div>

          <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-2xl border border-gray-200/80 shadow-xs space-y-3">
              <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center font-bold">
                1
              </div>
              <h3 className="text-base font-bold text-gray-900">Invisible Prerequisite Gaps</h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Textbooks and video lectures present advanced topics linearly without detecting when an underlying foundational dependency is broken.
              </p>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-gray-200/80 shadow-xs space-y-3">
              <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
                2
              </div>
              <h3 className="text-base font-bold text-gray-900">Passive Chatbot Answers</h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Generic AI chatbots provide instant full answers. Students feel like they understand in the moment, but fail during exams because no genuine concept retrieval was built.
              </p>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-gray-200/80 shadow-xs space-y-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
                3
              </div>
              <h3 className="text-base font-bold text-gray-900">Repeated-Question Illusions</h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Most platforms quiz students on questions they just saw. High scores measure short-term visual memorization, not verified retention.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 3: HOW COURSEPILOT WORKS */}
      <section id="how-it-works" className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <h2 className="text-xs font-bold uppercase tracking-wider text-indigo-600">The Solution</h2>
            <p className="mt-2 text-3xl font-extrabold text-gray-900 tracking-tight">
              An Adaptive System, Not a Chatbot
            </p>
            <p className="mt-3 text-base text-gray-500">
              CoursePilot combines syllabus document extraction, topological graph analysis, adaptive planning, and a Socratic AI tutor that verifies understanding.
            </p>
          </div>

          <div className="mt-14 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-5 rounded-2xl border border-gray-100 bg-white shadow-xs space-y-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <FileText className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-gray-900">1. Syllabus Ingestion</h4>
              <p className="text-xs text-gray-500 leading-relaxed">
                Upload your course PDF. The system extracts units, topics, and subtopics while preserving page-number references for exact citations.
              </p>
            </div>

            <div className="p-5 rounded-2xl border border-gray-100 bg-white shadow-xs space-y-3">
              <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
                <GitFork className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-gray-900">2. Prerequisite DAG</h4>
              <p className="text-xs text-gray-500 leading-relaxed">
                Builds an interactive Directed Acyclic Graph showing which foundational concepts must be mastered before advanced topics can be learned.
              </p>
            </div>

            <div className="p-5 rounded-2xl border border-gray-100 bg-white shadow-xs space-y-3">
              <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                <Award className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-gray-900">3. Diagnostic Engine</h4>
              <p className="text-xs text-gray-500 leading-relaxed">
                Evaluates existing knowledge, classifying each concept as Strong (&ge;80%), Developing (50-79%), Weak (&lt;50%), or Unassessed.
              </p>
            </div>

            <div className="p-5 rounded-2xl border border-gray-100 bg-white shadow-xs space-y-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <TrendingUp className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-gray-900">4. Verified Analytics</h4>
              <p className="text-xs text-gray-500 leading-relaxed">
                Fresh assessments exclude repeated questions to verify true post-learning improvement. Tracks exam readiness with reliability warnings.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 4: SIX-STAGE LEARNING WORKFLOW */}
      <section id="workflow" className="py-20 bg-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <h2 className="text-xs font-bold uppercase tracking-wider text-amber-400">The Student Journey</h2>
            <p className="mt-2 text-3xl font-extrabold tracking-tight">
              The 6-Stage Learning Recovery Pipeline
            </p>
            <p className="mt-3 text-sm text-gray-400">
              Every learner progresses through a disciplined Socratic pipeline that ensures concepts are thoroughly understood.
            </p>
          </div>

          <div className="mt-14 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-400 uppercase">Stage 01</span>
                <span className="text-xs text-gray-400 font-mono">UNDERSTAND</span>
              </div>
              <h3 className="text-lg font-bold text-white">Syllabus &amp; Structure</h3>
              <p className="text-xs text-gray-300 leading-relaxed">
                PDF parsing extracts hierarchical topics and connects prerequisite links into a verified knowledge graph.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-400 uppercase">Stage 02</span>
                <span className="text-xs text-gray-400 font-mono">DIAGNOSE</span>
              </div>
              <h3 className="text-lg font-bold text-white">Gap Identification</h3>
              <p className="text-xs text-gray-300 leading-relaxed">
                Targeted diagnostic tests evaluate initial topic-wise accuracy and identify foundational prerequisite bottlenecks.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-400 uppercase">Stage 03</span>
                <span className="text-xs text-gray-400 font-mono">PLAN</span>
              </div>
              <h3 className="text-lg font-bold text-white">Topological Roadmap</h3>
              <p className="text-xs text-gray-300 leading-relaxed">
                Kahn&apos;s topological sort schedules foundational blockers first, adapting to daily study minutes and upcoming exam dates.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-400 uppercase">Stage 04</span>
                <span className="text-xs text-gray-400 font-mono">TEACH</span>
              </div>
              <h3 className="text-lg font-bold text-white">Socratic AI Tutor</h3>
              <p className="text-xs text-gray-300 leading-relaxed">
                1-on-1 pedagogical dialogue in English, Hindi, or Hinglish with concrete code examples and exact syllabus citations.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-400 uppercase">Stage 05</span>
                <span className="text-xs text-gray-400 font-mono">VERIFY</span>
              </div>
              <h3 className="text-lg font-bold text-white">Interactive Practice</h3>
              <p className="text-xs text-gray-300 leading-relaxed">
                3-tier progressive hints guide students through problem solving without giving away the final answer prematurely.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-400 uppercase">Stage 06</span>
                <span className="text-xs text-gray-400 font-mono">IMPROVE</span>
              </div>
              <h3 className="text-lg font-bold text-white">Observable Progress</h3>
              <p className="text-xs text-gray-300 leading-relaxed">
                Fresh post-learning assessments record real percentage-point gains, updating topic mastery and exam readiness.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 5: ADAPTIVE AI TUTOR CAPABILITIES */}
      <section id="tutor" className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-purple-50 text-purple-700 text-xs font-semibold border border-purple-100">
                <BrainCircuit className="w-3.5 h-3.5" />
                <span>Pedagogical Socratic State Machine</span>
              </div>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight">
                An AI Tutor that doesn&apos;t give away answers.
              </h2>
              <p className="text-base text-gray-600 leading-relaxed">
                Unlike LLM chatbots that dump solutions, CoursePilot&apos;s AI tutor uses a guided pedagogical state machine:
              </p>
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <div className="p-1 rounded-md bg-indigo-50 text-indigo-600 mt-0.5">
                    <Check className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-gray-900">Multi-Language Explanations</h4>
                    <p className="text-xs text-gray-500">Switch seamlessly between English, Hindi, and Hinglish for intuitive understanding.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="p-1 rounded-md bg-indigo-50 text-indigo-600 mt-0.5">
                    <Check className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-gray-900">Grounded Syllabus Citations</h4>
                    <p className="text-xs text-gray-500">Every response references specific syllabus sections (e.g. <em>Source: Unit 2, Page 14</em>) to prevent hallucination.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="p-1 rounded-md bg-indigo-50 text-indigo-600 mt-0.5">
                    <Check className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-gray-900">3-Tier Progressive Hints</h4>
                    <p className="text-xs text-gray-500">Subtle directional cues first, followed by structural pointers, and finally direct application guidance.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Visual Chat Mockup */}
            <div className="bg-gray-50 rounded-2xl p-5 border border-gray-200 shadow-sm space-y-3">
              <div className="flex items-center justify-between pb-3 border-b border-gray-200 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="font-bold text-gray-800">AI Tutor &bull; Dynamic Programming State</span>
                </div>
                <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded font-semibold text-[10px]">
                  Hinglish &bull; Intermediate
                </span>
              </div>

              {/* Chat turns */}
              <div className="space-y-3 text-xs">
                <div className="p-3 bg-white rounded-xl border border-gray-100 shadow-2xs max-w-[85%] space-y-1">
                  <span className="font-bold text-indigo-600 block">Student</span>
                  <p className="text-gray-700">Sir, DP state kya hota hai? Recursion se kaise related hai?</p>
                </div>

                <div className="p-3 bg-indigo-50/60 rounded-xl border border-indigo-100 shadow-2xs ml-auto max-w-[90%] space-y-1.5">
                  <span className="font-bold text-indigo-900 block">CoursePilot Tutor</span>
                  <p className="text-gray-800">
                    DP state basically ek snapshot hai jo subproblem ko uniquely identify karta hai. Agar Recursion me parameters <code>(i, target)</code> hain, toh DP state <code>dp[i][target]</code> ban jata hai!
                  </p>
                  <div className="p-2 bg-white rounded-md border border-indigo-100 text-[11px] text-indigo-700 font-mono">
                    Citation: [Unit 2: Dynamic Programming, Page 12]
                  </div>
                </div>

                <div className="p-3 bg-emerald-50/70 rounded-xl border border-emerald-100 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-emerald-800">Practice Question Generated</span>
                    <span className="text-[10px] text-emerald-600 font-semibold">Active Verification</span>
                  </div>
                  <p className="text-gray-700">
                    If a recursive function has two changing variables: <code>index (0 to N)</code> and <code>weight (0 to W)</code>, what is the dimension of the required DP table?
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 6: KNOWLEDGE GRAPH & SECTION 7: EVIDENCE-BASED IMPROVEMENT */}
      <section className="py-20 bg-gray-50 border-t border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-16">
          {/* Knowledge Graph Preview */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
            <div className="space-y-4">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
                Knowledge Graph Engine
              </span>
              <h3 className="text-3xl font-extrabold text-gray-900 tracking-tight">
                See exactly which concept is blocking your progress.
              </h3>
              <p className="text-sm text-gray-600 leading-relaxed">
                Our Directed Acyclic Graph traces concept dependencies across the entire course. When you struggle with <em>Grid DP</em>, CoursePilot flags the real root bottleneck: <em>Recursion and Tabulation</em>.
              </p>
              <div className="p-3 bg-white rounded-xl border border-gray-200 text-xs text-gray-600 space-y-1">
                <span className="font-semibold text-gray-900">Bottleneck Impact Formula:</span>
                <p className="font-mono text-indigo-700">Impact = DependentCount &times; (1.0 - Mastery) &times; 10</p>
              </div>
            </div>

            <div className="p-6 bg-white rounded-2xl border border-gray-200 shadow-sm space-y-3">
              <div className="flex items-center justify-between text-xs font-bold text-gray-700 pb-2 border-b border-gray-100">
                <span>Prerequisite Dependency Chain</span>
                <span className="text-indigo-600">DAG Traversal</span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-between">
                  <span className="font-bold text-emerald-900">Recursion &amp; Base Cases</span>
                  <span className="text-emerald-700 font-semibold">100% Mastery &bull; Foundational</span>
                </div>
                <div className="text-center text-gray-400 font-bold">&darr;</div>
                <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-between">
                  <span className="font-bold text-amber-900">DP State &amp; Memoization</span>
                  <span className="text-amber-700 font-semibold">55% Mastery &bull; Developing</span>
                </div>
                <div className="text-center text-gray-400 font-bold">&darr;</div>
                <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-between">
                  <span className="font-bold text-rose-900">Grid DP &amp; Tabulation</span>
                  <span className="text-rose-700 font-semibold">20% Mastery &bull; Blocked</span>
                </div>
              </div>
            </div>
          </div>

          {/* Evidence-Based Learning Improvement */}
          <div className="p-8 bg-white rounded-2xl border border-gray-200 shadow-sm space-y-6">
            <div className="text-center max-w-2xl mx-auto space-y-2">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100 text-xs font-semibold">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Zero Duplicate Question Bias</span>
              </div>
              <h3 className="text-2xl font-extrabold text-gray-900">
                Evidence-Based Learning Verification
              </h3>
              <p className="text-xs text-gray-500">
                We measure learning gains by testing students on <strong>completely fresh questions</strong> that exclude baseline items. High scores reflect true concept mastery.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
              <div className="p-4 bg-gray-50 rounded-xl border border-gray-100">
                <span className="text-xs text-gray-400 block uppercase font-medium">Diagnostic Baseline</span>
                <span className="text-2xl font-bold text-gray-700 mt-1 block">35%</span>
                <span className="text-[11px] text-gray-500">Initial assessment score</span>
              </div>

              <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                <span className="text-xs text-emerald-700 block uppercase font-medium">Fresh Post-Learning Test</span>
                <span className="text-2xl font-bold text-emerald-900 mt-1 block">85%</span>
                <span className="text-[11px] text-emerald-600">Fresh unseen questions only</span>
              </div>

              <div className="p-4 bg-indigo-50 rounded-xl border border-indigo-100">
                <span className="text-xs text-indigo-700 block uppercase font-medium">Verified Improvement</span>
                <span className="text-2xl font-bold text-indigo-900 mt-1 block">+50 pp</span>
                <span className="text-[11px] text-indigo-600">Observed percentage point gain</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 8: WHY COURSEPILOT IS DIFFERENT */}
      <section id="comparison" className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-14">
            <h2 className="text-xs font-bold uppercase tracking-wider text-indigo-600">Comparison</h2>
            <p className="mt-2 text-3xl font-extrabold text-gray-900 tracking-tight">
              Why CoursePilot AI Stands Apart
            </p>
            <p className="mt-3 text-sm text-gray-500">
              Built specifically for deep academic learning and exam recovery, not generic conversation.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-gray-600 border border-gray-200 rounded-2xl overflow-hidden shadow-xs">
              <thead className="bg-gray-50 border-b border-gray-200 text-gray-900 font-bold uppercase text-[11px] tracking-wider">
                <tr>
                  <th className="p-4">Capability</th>
                  <th className="p-4 text-indigo-600 bg-indigo-50/50">CoursePilot AI</th>
                  <th className="p-4 text-gray-500">Generic LLM Chatbots</th>
                  <th className="p-4 text-gray-500">Static Practice Platforms</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr>
                  <td className="p-4 font-semibold text-gray-900">Root Gap Diagnosis</td>
                  <td className="p-4 bg-indigo-50/30 text-emerald-700 font-bold">Yes (Traces Prerequisite DAG)</td>
                  <td className="p-4 text-gray-400">No (Answers question in isolation)</td>
                  <td className="p-4 text-gray-400">No (Shows raw pass/fail count)</td>
                </tr>
                <tr>
                  <td className="p-4 font-semibold text-gray-900">Pedagogical Guardrails</td>
                  <td className="p-4 bg-indigo-50/30 text-emerald-700 font-bold">Yes (Socratic 6-stage machine)</td>
                  <td className="p-4 text-gray-400">No (Instantly reveals solutions)</td>
                  <td className="p-4 text-gray-400">No (Static answer keys)</td>
                </tr>
                <tr>
                  <td className="p-4 font-semibold text-gray-900">Language Flexibility</td>
                  <td className="p-4 bg-indigo-50/30 text-emerald-700 font-bold">English &bull; Hindi &bull; Hinglish</td>
                  <td className="p-4 text-gray-500">Variable / English-centric</td>
                  <td className="p-4 text-gray-400">English only</td>
                </tr>
                <tr>
                  <td className="p-4 font-semibold text-gray-900">Syllabus Grounding</td>
                  <td className="p-4 bg-indigo-50/30 text-emerald-700 font-bold">Yes (Exact page &amp; unit citations)</td>
                  <td className="p-4 text-gray-400">No (General web pretraining)</td>
                  <td className="p-4 text-gray-400">No (Generic question banks)</td>
                </tr>
                <tr>
                  <td className="p-4 font-semibold text-gray-900">Verified Improvement</td>
                  <td className="p-4 bg-indigo-50/30 text-emerald-700 font-bold">Yes (Excludes duplicate questions)</td>
                  <td className="p-4 text-gray-400">No (No assessment tracking)</td>
                  <td className="p-4 text-gray-400">No (Tests same repeated items)</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* SECTION 9: FINAL CALL TO ACTION */}
      <section className="py-20 bg-gradient-to-br from-indigo-900 via-indigo-800 to-indigo-950 text-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Stop studying in circles. Master your course concepts today.
          </h2>
          <p className="text-base text-indigo-200 max-w-xl mx-auto font-normal">
            Upload your syllabus, uncover foundational knowledge gaps, and study with an AI tutor that adapts until you truly understand.
          </p>
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to={isAuthenticated ? "/dashboard" : "/register"}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-8 py-4 rounded-xl text-base font-bold text-indigo-950 bg-amber-400 hover:bg-amber-300 shadow-lg transition-all hover:scale-102"
            >
              <span>{isAuthenticated ? "Go to Dashboard" : "Get Started Now"}</span>
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-100 py-8 text-center text-xs text-gray-400">
        CoursePilot AI &bull; Homingo Hackathon 2026 &bull; Track C3: A Tutor for Every Learner
      </footer>
    </div>
  );
};

export default LandingPage;
