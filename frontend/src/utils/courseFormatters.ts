import { Course } from '../types';

export const formatStudyMinutes = (minutes: number): string => {
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  if (remainder === 0) {
    return `${hours}h`;
  }
  return `${hours}h ${remainder}m`;
};

export const formatCalendarDate = (dateStr: string | null): string => {
  if (!dateStr) {
    return 'Not set';
  }
  const parts = dateStr.split('-').map(Number);
  if (parts.length !== 3 || parts.some((n) => Number.isNaN(n))) {
    return dateStr;
  }
  const [year, month, day] = parts;
  const localDate = new Date(year, month - 1, day);
  return localDate.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

export const formatTimestampDate = (isoStr: string): string => {
  const parsed = new Date(isoStr);
  if (Number.isNaN(parsed.getTime())) {
    return isoStr;
  }
  return parsed.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

export const isPastDateString = (dateStr: string): boolean => {
  if (!dateStr) {
    return false;
  }
  const parts = dateStr.split('-').map(Number);
  if (parts.length !== 3 || parts.some((n) => Number.isNaN(n))) {
    return false;
  }
  const [year, month, day] = parts;
  const candidate = new Date(year, month - 1, day);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return candidate < today;
};

export const getExamCountdownText = (course: Course): string => {
  if (!course.exam_date || course.days_remaining === null) {
    return 'No exam date set';
  }
  if (course.days_remaining === 0) {
    return 'Exam is today';
  }
  if (course.days_remaining > 0) {
    return course.days_remaining === 1
      ? '1 day remaining'
      : `${course.days_remaining} days remaining`;
  }
  const daysAgo = Math.abs(course.days_remaining);
  return daysAgo === 1
    ? 'Exam passed 1 day ago'
    : `Exam passed ${daysAgo} days ago`;
};

export interface CourseStatusMeta {
  label: string;
  badgeClassName: string;
}

export const getCourseStatusMeta = (course: Course): CourseStatusMeta => {
  switch (course.exam_status) {
    case 'passed':
      return {
        label: 'Exam Passed',
        badgeClassName: 'bg-amber-50 text-amber-700 border-amber-200',
      };
    case 'today':
      return {
        label: 'Exam Today',
        badgeClassName: 'bg-red-50 text-red-700 border-red-200',
      };
    case 'urgent':
      return {
        label: 'Exam Soon',
        badgeClassName: 'bg-orange-50 text-orange-700 border-orange-200',
      };
    case 'upcoming':
      return {
        label: 'Active',
        badgeClassName: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      };
    case 'no_exam_date':
    default:
      return {
        label: 'Self-Paced',
        badgeClassName: 'bg-indigo-50 text-indigo-700 border-indigo-200',
      };
  }
};

