import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  X,
} from 'lucide-react';
import {
  Course,
  CourseCreatePayload,
  CourseUpdatePayload,
} from '../types';
import { courseService } from '../services/courseService';
import { extractApiErrorMessage } from '../services/api';
import {
  CourseCard,
  CourseFormModal,
  DeleteCourseModal,
} from '../components/course';

interface CoursesLocationState {
  notice?: string;
}

export const Courses: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const [courses, setCourses] = useState<Course[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(() => {
    const state = location.state as CoursesLocationState | null;
    return state?.notice ?? null;
  });

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);
  const [deletingCourse, setDeletingCourse] = useState<Course | null>(null);

  useEffect(() => {
    const state = location.state as CoursesLocationState | null;
    if (state?.notice) {
      setNotice(state.notice);
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.pathname, location.state, navigate]);

  const fetchCourses = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const response = await courseService.getCourses();
      setCourses(response.data.courses);
    } catch (error) {
      setLoadError(
        extractApiErrorMessage(error, 'Failed to load your courses. Please try again.')
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchCourses();
  }, [fetchCourses]);

  const filteredCourses = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) {
      return courses;
    }
    return courses.filter(
      (course) =>
        course.title.toLowerCase().includes(query) ||
        (course.description && course.description.toLowerCase().includes(query))
    );
  }, [courses, searchQuery]);

  const handleCreateCourse = async (
    payload: CourseCreatePayload | CourseUpdatePayload
  ) => {
    const response = await courseService.createCourse(payload as CourseCreatePayload);
    setCourses((prev) => [response.data, ...prev]);
    setIsCreateModalOpen(false);
    setNotice(`Course "${response.data.title}" created successfully.`);
  };

  const handleUpdateCourse = async (
    payload: CourseCreatePayload | CourseUpdatePayload
  ) => {
    if (!editingCourse) {
      return;
    }
    const response = await courseService.updateCourse(
      editingCourse.id,
      payload as CourseUpdatePayload
    );
    setCourses((prev) =>
      prev.map((item) => (item.id === response.data.id ? response.data : item))
    );
    setEditingCourse(null);
    setNotice(`Course "${response.data.title}" updated successfully.`);
  };

  const handleDeleteCourse = async (course: Course) => {
    await courseService.deleteCourse(course.id);
    setCourses((prev) => prev.filter((item) => item.id !== course.id));
    setDeletingCourse(null);
    setNotice(`Course "${course.title}" was deleted.`);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">My Courses</h1>
            {!isLoading && !loadError && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-100">
                {courses.length} {courses.length === 1 ? 'course' : 'courses'}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Organize the subjects you are studying, set exam dates, and configure your daily study time.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsCreateModalOpen(true)}
          className="inline-flex items-center justify-center space-x-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-colors self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Create Course</span>
        </button>
      </div>

      {notice && (
        <div
          role="status"
          className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
        >
          <div className="flex items-center space-x-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{notice}</span>
          </div>
          <button
            type="button"
            onClick={() => setNotice(null)}
            aria-label="Dismiss notification"
            className="p-1 rounded text-emerald-700 hover:bg-emerald-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {!isLoading && !loadError && courses.length > 0 && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="relative w-full sm:max-w-sm">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search courses by title or description..."
              aria-label="Search courses"
              className="w-full rounded-lg border border-gray-300 bg-white pl-9 pr-9 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                aria-label="Clear search"
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-gray-400 hover:text-gray-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {searchQuery.trim() && (
            <p className="text-xs text-gray-500">
              Showing {filteredCourses.length} of {courses.length}{' '}
              {courses.length === 1 ? 'course' : 'courses'}
            </p>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 flex flex-col items-center justify-center text-center">
          <Loader2 className="w-7 h-7 text-indigo-600 animate-spin" />
          <p className="mt-3 text-sm font-medium text-gray-700">Loading your courses...</p>
        </div>
      ) : loadError ? (
        <div className="bg-white rounded-xl border border-red-200 p-8 text-center">
          <div className="mx-auto w-11 h-11 rounded-full bg-red-50 text-red-600 flex items-center justify-center">
            <AlertCircle className="w-5 h-5" />
          </div>
          <h2 className="mt-3 text-base font-semibold text-gray-900">
            Could not load courses
          </h2>
          <p className="mt-1 text-sm text-gray-500 max-w-md mx-auto">{loadError}</p>
          <button
            type="button"
            onClick={() => void fetchCourses()}
            className="mt-4 inline-flex items-center space-x-2 rounded-lg bg-white border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Try Again</span>
          </button>
        </div>
      ) : courses.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <div className="mx-auto w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <BookOpen className="w-6 h-6" />
          </div>
          <h2 className="mt-4 text-lg font-semibold text-gray-900">No courses yet</h2>
          <p className="mt-1.5 text-sm text-gray-500 max-w-md mx-auto">
            Create your first course—such as Data Structures and Algorithms, Machine Learning, or
            Database Management Systems—to start tracking exam dates and daily study time.
          </p>
          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            className="mt-5 inline-flex items-center space-x-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Create Your First Course</span>
          </button>
        </div>
      ) : filteredCourses.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-10 text-center">
          <Search className="w-8 h-8 text-gray-300 mx-auto" />
          <h2 className="mt-3 text-base font-semibold text-gray-900">
            No matching courses
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            No courses matched &ldquo;{searchQuery.trim()}&rdquo;.
          </p>
          <button
            type="button"
            onClick={() => setSearchQuery('')}
            className="mt-4 inline-flex items-center space-x-1.5 rounded-lg border border-gray-300 bg-white px-3.5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <span>Clear search</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredCourses.map((course) => (
            <CourseCard
              key={course.id}
              course={course}
              onEdit={(selected) => setEditingCourse(selected)}
              onDelete={(selected) => setDeletingCourse(selected)}
            />
          ))}
        </div>
      )}

      <CourseFormModal
        isOpen={isCreateModalOpen}
        mode="create"
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateCourse}
      />

      <CourseFormModal
        isOpen={Boolean(editingCourse)}
        mode="edit"
        initialCourse={editingCourse}
        onClose={() => setEditingCourse(null)}
        onSubmit={handleUpdateCourse}
      />

      <DeleteCourseModal
        course={deletingCourse}
        onClose={() => setDeletingCourse(null)}
        onConfirm={handleDeleteCourse}
      />
    </div>
  );
};

export default Courses;

