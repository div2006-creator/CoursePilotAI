import React from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Calendar,
  Clock,
  Pencil,
  Trash2,
} from 'lucide-react';
import { Course } from '../../types';
import {
  formatCalendarDate,
  formatStudyMinutes,
  getCourseStatusMeta,
  getExamCountdownText,
} from '../../utils/courseFormatters';

interface CourseCardProps {
  course: Course;
  onEdit: (course: Course) => void;
  onDelete: (course: Course) => void;
}

export const CourseCard: React.FC<CourseCardProps> = ({
  course,
  onEdit,
  onDelete,
}) => {
  const statusMeta = getCourseStatusMeta(course);
  const countdownText = getExamCountdownText(course);

  return (
    <article className="bg-white rounded-xl border border-gray-200 shadow-sm hover:border-indigo-200 hover:shadow transition-all flex flex-col justify-between">
      <div className="p-5 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <Link
            to={`/courses/${course.id}`}
            className="text-base font-semibold text-gray-900 hover:text-indigo-600 transition-colors line-clamp-2 leading-snug"
          >
            {course.title}
          </Link>
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border whitespace-nowrap flex-shrink-0 ${statusMeta.badgeClassName}`}
          >
            {statusMeta.label}
          </span>
        </div>

        <p className="text-sm text-gray-600 line-clamp-2 min-h-[2.5rem]">
          {course.description ? (
            course.description
          ) : (
            <span className="text-gray-400 italic">No description added yet.</span>
          )}
        </p>

        <div className="grid grid-cols-2 gap-3 pt-1">
          <div className="rounded-lg bg-gray-50 border border-gray-100 p-2.5">
            <div className="flex items-center space-x-1.5 text-xs text-gray-500">
              <Calendar className="w-3.5 h-3.5 text-gray-400" />
              <span>Exam Date</span>
            </div>
            <p className="mt-1 text-sm font-medium text-gray-900 truncate">
              {formatCalendarDate(course.exam_date)}
            </p>
            <p
              className={`text-xs mt-0.5 truncate ${
                course.is_exam_passed
                  ? 'text-amber-700 font-medium'
                  : course.exam_status === 'today' || course.exam_status === 'urgent'
                    ? 'text-orange-700 font-medium'
                    : 'text-gray-500'
              }`}
            >
              {countdownText}
            </p>
          </div>

          <div className="rounded-lg bg-gray-50 border border-gray-100 p-2.5">
            <div className="flex items-center space-x-1.5 text-xs text-gray-500">
              <Clock className="w-3.5 h-3.5 text-gray-400" />
              <span>Daily Study</span>
            </div>
            <p className="mt-1 text-sm font-medium text-gray-900">
              {formatStudyMinutes(course.daily_minutes)} / day
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {course.daily_minutes} min daily
            </p>
          </div>
        </div>

        <div className="space-y-1.5 pt-1">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-gray-600">Learning Progress</span>
            <span className="text-gray-400">Mastery tracking coming soon</span>
          </div>
          <div
            className="h-1.5 w-full rounded-full bg-gray-100 overflow-hidden"
            aria-label="Course progress placeholder"
          >
            <div className="h-full w-0 rounded-full bg-indigo-500" />
          </div>
        </div>
      </div>

      <div className="px-5 py-3 bg-gray-50/70 border-t border-gray-100 rounded-b-xl flex items-center justify-between">
        <Link
          to={`/courses/${course.id}`}
          className="inline-flex items-center space-x-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
        >
          <span>View Details</span>
          <ArrowRight className="w-4 h-4" />
        </Link>

        <div className="flex items-center space-x-1">
          <button
            type="button"
            onClick={() => onEdit(course)}
            aria-label={`Edit ${course.title}`}
            title="Edit course"
            className="p-1.5 rounded-lg text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => onDelete(course)}
            aria-label={`Delete ${course.title}`}
            title="Delete course"
            className="p-1.5 rounded-lg text-gray-500 hover:text-red-600 hover:bg-red-50 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </article>
  );
};

