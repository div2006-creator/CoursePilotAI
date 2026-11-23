import React, { useState } from 'react';
import {
  Bot,
  User,
  Check,
  Copy,
  BookOpen,
  ChevronDown,
  ChevronUp,
  FileText,
} from 'lucide-react';
import { TutorMessage, TutorSourceCitation } from '../../types';

interface ChatMessageProps {
  message: TutorMessage;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isTutor = message.role === 'assistant' || message.role === 'system';
  const [copiedCodeIndex, setCopiedCodeIndex] = useState<number | null>(null);
  const [showSources, setShowSources] = useState(false);

  const handleCopyCode = async (code: string, index: number) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCodeIndex(index);
      setTimeout(() => setCopiedCodeIndex(null), 2000);
    } catch {
      // ignore
    }
  };

  // Helper to render markdown-like content (code blocks, bold, bullet points)
  const renderFormattedContent = (content: string) => {
    // Split by code blocks ```lang ... ```
    const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g;
    const parts = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;
    let blockCount = 0;

    while ((match = codeBlockRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: content.substring(lastIndex, match.index),
          key: `text-${lastIndex}`,
        });
      }

      const lang = match[1] || 'java';
      const code = match[2];
      const currentBlockIndex = blockCount++;
      parts.push({
        type: 'code',
        lang,
        content: code,
        index: currentBlockIndex,
        key: `code-${match.index}`,
      });

      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < content.length) {
      parts.push({
        type: 'text',
        content: content.substring(lastIndex),
        key: `text-${lastIndex}`,
      });
    }

    return (
      <div className="space-y-3">
        {parts.map((part) => {
          if (part.type === 'code') {
            const isCopied = copiedCodeIndex === part.index;
            return (
              <div
                key={part.key}
                className="my-3 rounded-xl overflow-hidden bg-gray-900 border border-gray-800 text-gray-100 shadow-md"
              >
                <div className="flex items-center justify-between px-3.5 py-1.5 bg-gray-950/80 border-b border-gray-800 text-xs text-gray-400 font-mono">
                  <span>{part.lang || 'code'}</span>
                  <button
                    type="button"
                    onClick={() => handleCopyCode(part.content || '', part.index || 0)}
                    className="flex items-center space-x-1 hover:text-gray-200 transition-colors"
                  >
                    {isCopied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-3.5 text-xs font-mono overflow-x-auto leading-relaxed">
                  <code>{part.content}</code>
                </pre>
              </div>
            );
          }

          // Plain text with line breaks and bold formatting
          const paragraphs = (part.content || '').split('\n\n');
          return (
            <div key={part.key} className="space-y-2 text-sm leading-relaxed">
              {paragraphs.map((p, pIdx) => {
                const lines = p.split('\n');
                return (
                  <p key={pIdx}>
                    {lines.map((line, lIdx) => (
                      <React.Fragment key={lIdx}>
                        {lIdx > 0 && <br />}
                        {renderInlineFormatting(line)}
                      </React.Fragment>
                    ))}
                  </p>
                );
              })}
            </div>
          );
        })}
      </div>
    );
  };

  const renderInlineFormatting = (text: string) => {
    // Bold: **text**
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, idx) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={idx} className="font-semibold text-gray-900">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code
            key={idx}
            className="px-1.5 py-0.5 rounded-md bg-gray-100 text-indigo-700 font-mono text-xs"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  const getMessageTypeBadge = (type: string) => {
    switch (type) {
      case 'explanation':
        return (
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
            Explanation
          </span>
        );
      case 'example':
        return (
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">
            Trace & Example
          </span>
        );
      case 'practice_question':
        return (
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
            Practice Problem
          </span>
        );
      case 'hint':
        return (
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
            Socratic Hint
          </span>
        );
      case 'evaluation':
        return (
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">
            Assessment
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div
      className={`flex items-start space-x-3 ${
        isTutor ? 'justify-start' : 'justify-end flex-row-reverse space-x-reverse'
      }`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-white shadow-xs ${
          isTutor
            ? 'bg-gradient-to-tr from-indigo-600 to-violet-600'
            : 'bg-gradient-to-tr from-gray-700 to-gray-900'
        }`}
      >
        {isTutor ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
      </div>

      {/* Message Bubble Container */}
      <div
        className={`max-w-2xl rounded-2xl p-4 shadow-2xs border ${
          isTutor
            ? 'bg-white border-gray-200 text-gray-800'
            : 'bg-indigo-600 border-indigo-500 text-white'
        }`}
      >
        {/* Header Meta */}
        <div className="flex items-center space-x-2 mb-2">
          <span
            className={`text-xs font-semibold ${
              isTutor ? 'text-gray-900' : 'text-indigo-100'
            }`}
          >
            {isTutor ? 'CoursePilot Tutor' : 'You'}
          </span>
          {isTutor && getMessageTypeBadge(message.message_type)}
          <span
            className={`text-[10px] ${
              isTutor ? 'text-gray-400' : 'text-indigo-200'
            }`}
          >
            {new Date(message.created_at).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>

        {/* Message Content */}
        <div className={isTutor ? 'text-gray-800' : 'text-indigo-50'}>
          {renderFormattedContent(message.content)}
        </div>

        {/* Citations / Grounded Course Material Sources */}
        {isTutor && message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-2.5 border-t border-gray-100">
            <button
              type="button"
              onClick={() => setShowSources(!showSources)}
              className="flex items-center space-x-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>
                {message.sources.length} Grounded Course Reference
                {message.sources.length > 1 ? 's' : ''}
              </span>
              {showSources ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
            </button>

            {showSources && (
              <div className="mt-2 space-y-2">
                {message.sources.map((src: TutorSourceCitation, idx: number) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-lg bg-gray-50 border border-gray-200 text-xs text-gray-600"
                  >
                    <div className="flex items-center space-x-1.5 font-semibold text-gray-800 mb-1">
                      <FileText className="w-3.5 h-3.5 text-gray-400" />
                      <span>
                        {src.unit_name || 'Course Document'}
                        {src.page_number ? ` • Page ${src.page_number}` : ''}
                      </span>
                    </div>
                    {src.snippet && (
                      <p className="italic text-gray-500 line-clamp-3 pl-5 border-l-2 border-indigo-200">
                        "{src.snippet}"
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
