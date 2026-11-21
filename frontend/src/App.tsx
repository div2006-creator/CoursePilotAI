import React from 'react';
import {
  BrowserRouter as Router,
  Navigate,
  Outlet,
  Route,
  Routes,
} from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/common/Navbar';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { Dashboard } from './pages/Dashboard';
import { Courses } from './pages/Courses';
import { CourseDetails } from './pages/CourseDetails';
import { Diagnostic } from './pages/Diagnostic';
import { DiagnosticResult } from './pages/DiagnosticResult';
import { Topics } from './pages/Topics';
import { KnowledgeGraph } from './pages/KnowledgeGraph';
import { KnowledgeGaps } from './pages/KnowledgeGaps';
import { TutorPage } from './pages/TutorPage';
import { StudyPlanPage } from './pages/StudyPlanPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { NotFoundPage } from './pages/NotFoundPage';

const AuthenticatedLayout: React.FC = () => (
  <ProtectedRoute>
    <div className="min-h-screen flex flex-col bg-gray-50 text-gray-900">
      <Navbar />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
      <footer className="bg-white border-t border-gray-200 py-4 text-center text-xs text-gray-400">
        CoursePilot AI &bull; Personalized Learning Recovery Platform
      </footer>
    </div>
  </ProtectedRoute>
);

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route element={<AuthenticatedLayout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/courses" element={<Courses />} />
            <Route path="/courses/:courseId" element={<CourseDetails />} />
            <Route path="/courses/:courseId/diagnostic" element={<Diagnostic />} />
            <Route path="/courses/:courseId/diagnostic/:sessionId/result" element={<DiagnosticResult />} />
            <Route path="/courses/:courseId/topics" element={<Topics />} />
            <Route path="/courses/:courseId/graph" element={<KnowledgeGraph />} />
            <Route path="/courses/:courseId/knowledge-gaps" element={<KnowledgeGaps />} />
            <Route path="/tutor" element={<TutorPage />} />
            <Route path="/study-plan" element={<StudyPlanPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;
