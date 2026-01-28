import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message } from '../types';
import { BotAvatar } from './BotAvatar';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isBot = message.sender === 'bot';

  return (
    <div className={`flex w-full mb-6 ${isBot ? 'justify-start' : 'justify-end animate-in slide-in-from-right-4 duration-300'}`}>
      <div className={`flex max-w-[85%] md:max-w-[70%] ${isBot ? 'flex-row' : 'flex-row-reverse'}`}>
        {isBot && (
          <div className="mt-1 mr-3 flex-shrink-0">
            <BotAvatar />
          </div>
        )}

        <div className="flex flex-col">
          <div
            className={`px-4 py-3 shadow-md ${isBot
              ? 'bg-white text-slate-800 border border-slate-200 bot-bubble rounded-2xl'
              : 'bg-green-700 text-white user-bubble rounded-2xl'
              } ${message.isError ? 'border-red-500 bg-red-50 text-red-900' : ''}`}
          >
            {message.isError && <i className="fa-solid fa-circle-exclamation mr-2"></i>}

            {/* ✅ ReactMarkdown with proper v8+ API */}
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p className="whitespace-pre-wrap leading-relaxed text-sm md:text-base">{children}</p>,
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 underline hover:text-blue-800"
                  >
                    {children}
                  </a>
                ),
                li: ({ children }) => <li className="ml-4 list-disc">{children}</li>,
              }}
            >
              {message.text}
            </ReactMarkdown>

            {isBot && message.sources && message.sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-100">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Legal Footprints:
                </p>
                <div className="flex flex-wrap gap-2">
                  {message.sources.map((source, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px] border border-slate-200 hover:bg-slate-200 transition-colors cursor-default"
                    >
                      {source.startsWith('http') ? (
                        <a href={source} target="_blank" rel="noopener noreferrer">
                          {source}
                        </a>
                      ) : (
                        source
                      )}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className={`flex items-center mt-1 text-[10px] text-slate-400 px-1 ${isBot ? 'justify-start' : 'justify-end'}`}>
            <span>{message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            {message.tokensUsed !== undefined && (
              <>
                <span className="mx-1">•</span>
                <span>{message.tokensUsed} brain cells used</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
