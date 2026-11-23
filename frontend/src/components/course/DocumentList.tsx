import React, { useState } from 'react';
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  RefreshCw,
  Plus,
  Loader2,
} from 'lucide-react';
import { CourseDocument } from '../../types';
import { documentService } from '../../services/documentService';
import { extractApiErrorMessage } from '../../services/api';

interface DocumentListProps {
  documents: CourseDocument[];
  courseId: string;
  onRefresh: () => void;
  onOpenUpload: () => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  courseId,
  onRefresh,
  onOpenUpload,
}) => {
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleDelete = async (docId: string) => {
    if (!window.confirm('Are you sure you want to delete this document and its indexed chunks?')) {
      return;
    }
    setDeletingId(docId);
    setActionError(null);
    try {
      await documentService.deleteCourseDocument(courseId, docId);
      onRefresh();
    } catch (err) {
      setActionError(extractApiErrorMessage(err, 'Failed to delete document.'));
    } finally {
      setDeletingId(null);
    }
  };

  const handleRetry = async (docId: string) => {
    setRetryingId(docId);
    setActionError(null);
    try {
      await documentService.retryCourseDocument(courseId, docId);
      onRefresh();
    } catch (err) {
      setActionError(extractApiErrorMessage(err, 'Failed to retry document processing.'));
    } finally {
      setRetryingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3" /> Indexed
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
            <Loader2 className="w-3 h-3 animate-spin" /> Processing
          </span>
        );
      case 'ocr_required':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3 h-3" /> OCR Needed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertTriangle className="w-3 h-3" /> Failed
          </span>
        );
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-gray-900">Syllabus &amp; Study Materials</h3>
            <p className="text-xs text-gray-500">
              {documents.length} document{documents.length === 1 ? '' : 's'} indexed for topic extraction &amp; AI tutoring
            </p>
          </div>
        </div>

        <button
          onClick={onOpenUpload}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Upload PDF</span>
        </button>
      </div>

      {actionError && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800">
          {actionError}
        </div>
      )}

      {documents.length > 0 ? (
        <div className="divide-y divide-gray-100 border border-gray-100 rounded-lg overflow-hidden">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="p-3.5 bg-white hover:bg-gray-50/70 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
            >
              <div className="flex items-center gap-3 min-w-0">
                <FileText className="w-5 h-5 text-indigo-500 shrink-0" />
                <div className="min-w-0">
                  <div className="font-semibold text-gray-900 truncate">{doc.filename}</div>
                  <div className="text-[11px] text-gray-400 mt-0.5 flex flex-wrap items-center gap-2">
                    {doc.page_count && <span>{doc.page_count} pages</span>}
                    {doc.chunk_count > 0 && (
                      <>
                        <span>&bull;</span>
                        <span>{doc.chunk_count} text chunks</span>
                      </>
                    )}
                    {doc.file_size && (
                      <>
                        <span>&bull;</span>
                        <span>{(doc.file_size / (1024 * 1024)).toFixed(1)} MB</span>
                      </>
                    )}
                  </div>
                  {doc.error_message && (
                    <div className="text-[11px] text-rose-600 mt-1 max-w-md">
                      {doc.error_message}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3 self-end sm:self-center">
                {getStatusBadge(doc.status)}

                {doc.status.toLowerCase() === 'failed' && (
                  <button
                    onClick={() => handleRetry(doc.id)}
                    disabled={retryingId === doc.id}
                    title="Retry extraction"
                    className="p-1.5 text-gray-400 hover:text-indigo-600 rounded-md hover:bg-gray-100 transition-colors"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${retryingId === doc.id ? 'animate-spin' : ''}`} />
                  </button>
                )}

                <button
                  onClick={() => handleDelete(doc.id)}
                  disabled={deletingId === doc.id}
                  title="Delete document"
                  className="p-1.5 text-gray-400 hover:text-rose-600 rounded-md hover:bg-gray-100 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-8 text-center border border-dashed border-gray-200 rounded-lg space-y-3">
          <FileText className="w-8 h-8 text-gray-300 mx-auto" />
          <div>
            <p className="text-xs font-semibold text-gray-700">No Syllabus Uploaded Yet</p>
            <p className="text-[11px] text-gray-400 max-w-sm mx-auto mt-0.5">
              Upload your course syllabus or lecture notes in PDF format. CoursePilot AI will parse topics, subtopics, and prerequisite dependencies.
            </p>
          </div>
          <button
            onClick={onOpenUpload}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg text-xs font-semibold transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Upload Syllabus PDF</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default DocumentList;
