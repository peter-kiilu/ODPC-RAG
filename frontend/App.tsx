
import React, { useState, useRef, useEffect } from 'react';
import { Message } from './types';
import { apiService } from './services/apiService';
import { MessageBubble } from './components/MessageBubble';

const FUNNY_LOADING_MESSAGES = [
  "Consulting the Kenyan Constitution...",
  "Sharpening the Data Protection tools...",
  "Waking up the digital watchdog...",
  "Checking for cookies (not the eating kind)...",
  "Ensuring your privacy is properly tucked in...",
  "Asking the server for permission to speak...",
  "Filtering out prying eyes...",
  "Encrypting these thoughts...",
  "Locating the relevant clauses..."
];

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      text: "Hujambo! I am your ODPC Kenya Bot. I safeguard your data with the power of the law and the speed of a gazelle. How can I help you today?",
      sender: 'bot',
      timestamp: new Date(),
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState(FUNNY_LOADING_MESSAGES[0]);
  const [botHealth, setBotHealth] = useState<boolean | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  useEffect(() => {
    checkHealth();
    // Refresh health every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const health = await apiService.checkHealth();
      setBotHealth(health.Status === 'Active');
    } catch (e) {
      setBotHealth(false);
    }
  };

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  };

  const handleSend = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      text: inputText,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputText('');
    setIsLoading(true);

    // Rotate funny messages
    let msgIndex = 0;
    const interval = setInterval(() => {
      msgIndex = (msgIndex + 1) % FUNNY_LOADING_MESSAGES.length;
      setLoadingMsg(FUNNY_LOADING_MESSAGES[msgIndex]);
    }, 2000);

    try {
      const result = await apiService.sendMessage(inputText);
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: result.response,
        sender: 'bot',
        timestamp: new Date(),
        sources: result.sources,
        tokensUsed: result.tokens_used
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (error: any) {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: `Kusema kweli, something went wrong: ${error.message}`,
        sender: 'bot',
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      clearInterval(interval);
      setIsLoading(false);
    }
  };

  const handleClear = async () => {
    if (window.confirm("Are you sure? This will delete the bot's temporary memories!")) {
      try {
        await apiService.clearHistory();
        setMessages([
          {
            id: 'welcome-reset',
            text: "Brain wiped! I'm as fresh as a morning in the Rift Valley. What's on your mind?",
            sender: 'bot',
            timestamp: new Date(),
          }
        ]);
      } catch (e: any) {
        alert(e.message);
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full max-w-5xl mx-auto shadow-2xl bg-white overflow-hidden border-x border-slate-200">
      {/* Header */}
      <header className="px-6 py-4 glass border-b border-slate-200 flex items-center justify-between sticky top-0 z-20">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-green-700 flex items-center justify-center text-white shadow-lg">
            <i className="fa-solid fa-gavel"></i>
          </div>
          <div>
            <h1 className="font-bold text-slate-800 text-lg">ODPC Kenya Bot</h1>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${botHealth === true ? 'bg-green-500 animate-pulse' : botHealth === false ? 'bg-red-500' : 'bg-slate-300'}`}></span>
              <span className="text-[10px] font-medium text-slate-500 uppercase tracking-widest">
                {botHealth === true ? 'Operational & Vigilant' : botHealth === false ? 'Sleeping on duty' : 'Checking status...'}
              </span>
            </div>
          </div>
        </div>
        <button
          onClick={handleClear}
          className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
          title="Clear memory"
        >
          <i className="fa-solid fa-trash-can"></i>
        </button>
      </header>

      {/* Chat Area */}
      <main
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 md:p-8 bg-slate-50/50"
      >
        <div className="max-w-3xl mx-auto">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {isLoading && (
            <div className="flex w-full mb-6 justify-start">
              <div className="flex flex-row">
                <div className="mt-1 mr-3 flex-shrink-0 animate-bounce">
                  <div className="w-10 h-10 rounded-full bg-slate-200 border-2 border-slate-300 flex items-center justify-center">
                    <i className="fa-solid fa-microchip text-slate-400"></i>
                  </div>
                </div>
                <div className="flex flex-col">
                  <div className="px-5 py-3 bg-white border border-slate-200 rounded-2xl rounded-bl-none shadow-sm flex items-center gap-3">
                    <div className="flex gap-1">
                      <div className="w-1.5 h-1.5 bg-green-600 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                      <div className="w-1.5 h-1.5 bg-red-600 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                      <div className="w-1.5 h-1.5 bg-black rounded-full animate-bounce"></div>
                    </div>
                    <span className="text-sm text-slate-500 italic font-medium">{loadingMsg}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Input Area */}
      <footer className="p-4 md:p-6 bg-white border-t border-slate-100 sticky bottom-0">
        <div className="max-w-3xl mx-auto flex items-end gap-3">
          <div className="flex-1 relative group">
            <input
              ref={inputRef}
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Ask about data protection..."
              className="w-full pl-5 pr-12 py-4 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-green-600/20 focus:border-green-600 transition-all text-slate-800 placeholder:text-slate-400 shadow-inner"
              disabled={isLoading}
            />
            <div className="absolute right-4 bottom-4 text-slate-300">
              <i className="fa-solid fa-keyboard"></i>
            </div>
          </div>
          <button
            onClick={handleSend}
            disabled={!inputText.trim() || isLoading}
            className={`h-14 w-14 rounded-2xl flex items-center justify-center shadow-lg transition-all ${!inputText.trim() || isLoading
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                : 'bg-green-700 text-white hover:bg-green-800 hover:scale-105 active:scale-95'
              }`}
          >
            <i className={`fa-solid ${isLoading ? 'fa-spinner fa-spin' : 'fa-paper-plane'} text-lg`}></i>
          </button>
        </div>
        <p className="text-center mt-3 text-[10px] text-slate-400 font-medium uppercase tracking-widest">
          Powered by Justice & Data Privacy • Republic of Kenya
        </p>
      </footer>
    </div>
  );
};

export default App;
