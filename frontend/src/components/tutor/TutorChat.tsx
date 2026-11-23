import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles, MessageSquare } from 'lucide-react';
import { TutorMessage } from '../../types';
import { ChatMessage } from './ChatMessage';

interface TutorChatProps {
  messages: TutorMessage[];
  onSendMessage: (content: string) => Promise<void>;
  suggestedAction?: string;
  isSending?: boolean;
  disabled?: boolean;
}

const QUICK_ACTIONS = [
  'Give me an intuitive example with dry run',
  'Explain in simpler terms',
  'Give me a practice problem',
  'What are common edge cases?',
  'Check my understanding on this',
];

export const TutorChat: React.FC<TutorChatProps> = ({
  messages,
  onSendMessage,
  suggestedAction,
  isSending = false,
  disabled = false,
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isSending || disabled) return;

    const text = inputText.trim();
    setInputText('');
    await onSendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleQuickAction = (actionText: string) => {
    if (isSending || disabled) return;
    onSendMessage(actionText);
  };

  return (
    <div className="flex flex-col h-[650px] bg-gray-50/60 rounded-2xl border border-gray-200 overflow-hidden shadow-xs">
      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 text-gray-400">
            <MessageSquare className="w-12 h-12 text-gray-300 mb-3" />
            <h3 className="text-base font-semibold text-gray-700">
              Welcome to your 1-on-1 AI Tutoring Session
            </h3>
            <p className="text-xs text-gray-500 max-w-sm mt-1">
              Ask questions, request intuitive code traces, or test your understanding with practice problems.
            </p>
          </div>
        ) : (
          messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)
        )}

        {/* Loading / Typing Indicator */}
        {isSending && (
          <div className="flex items-center space-x-2 text-gray-500 text-xs italic bg-white border border-gray-200 py-2.5 px-4 rounded-2xl w-fit shadow-2xs">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
            <span>CoursePilot Tutor is reasoning and checking course sources...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Actions & Quick Prompts */}
      <div className="border-t border-gray-200 bg-white p-3 space-y-2">
        {suggestedAction && (
          <div className="flex items-center space-x-1.5 text-xs text-indigo-700 font-medium px-2">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>Suggested: {suggestedAction}</span>
          </div>
        )}

        <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 text-xs">
          {QUICK_ACTIONS.map((action, idx) => (
            <button
              key={idx}
              type="button"
              disabled={isSending || disabled}
              onClick={() => handleQuickAction(action)}
              className="whitespace-nowrap px-2.5 py-1 rounded-full bg-gray-100 hover:bg-indigo-50 hover:text-indigo-700 text-gray-600 border border-gray-200 hover:border-indigo-200 transition-colors text-[11px] font-medium"
            >
              {action}
            </button>
          ))}
        </div>

        {/* Text Input Box */}
        <form onSubmit={handleSubmit} className="flex items-end space-x-2">
          <div className="flex-1 relative">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isSending || disabled}
              placeholder="Ask a question, explain in your own words, or ask for examples (Enter to send)..."
              rows={2}
              className="w-full resize-none rounded-xl border border-gray-300 p-2.5 text-sm text-gray-900 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
            />
          </div>

          <button
            type="submit"
            disabled={!inputText.trim() || isSending || disabled}
            className="p-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50 transition-all shadow-xs flex-shrink-0"
            title="Send Message"
          >
            {isSending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

