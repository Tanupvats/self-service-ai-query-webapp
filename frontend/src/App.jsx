import React, { useState, useEffect, useRef } from 'react';
import { 
  Database, Upload, Play, ThumbsUp, ThumbsDown, 
  MessageSquare, Info, Send, Bot, User, Check, AlertCircle, FileText, Table
} from 'lucide-react';

// Connects to our Python FastAPI Backend
const BACKEND_URL = "http://localhost:8000/api/chat";
const TABLE_NAME = "uploaded_data";

const PRESET_QUERIES = [
  {
    id: 1,
    title: "High Risk Active Loans",
    description: "Filters the database for all loans currently marked as 'Active' with a 'High' risk rating.",
    query: "Show me all active loans with a High risk rating."
  },
  {
    id: 2,
    title: "Portfolio by RM",
    description: "Aggregates total loan amounts managed by each Relationship Manager.",
    query: "What is the total loan amount managed by each RM?"
  },
  {
    id: 3,
    title: "Defaulted Client List",
    description: "Lists all client names and amounts for loans that have defaulted.",
    query: "List all defaulted loans and their associated clients."
  }
];

export default function App() {
  const [isEngineReady, setIsEngineReady] = useState(false);
  const [schemaContext, setSchemaContext] = useState("No data uploaded yet. Inform the user they must upload a CSV file first.");
  const [clarificationTurns, setClarificationTurns] = useState(0);
  
  // Chat State
  const [messages, setMessages] = useState([
    { 
      id: 1, 
      role: 'assistant', 
      type: 'text', 
      content: "Hello! I'm your AI SQL Agent. Please upload a CSV dataset to begin, then you can ask me to generate queries against it." 
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // Active Execution State
  const [queryResults, setQueryResults] = useState(null);
  const [queryError, setQueryError] = useState('');
  const [feedbackState, setFeedbackState] = useState({});

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Init Local AlaSQL Engine
  useEffect(() => {
    const initDB = async () => {
      try {
        if (!window.alasql) {
          const script = document.createElement('script');
          script.src = 'https://cdn.jsdelivr.net/npm/alasql@4.2.2/dist/alasql.min.js';
          await new Promise(res => { script.onload = res; document.head.appendChild(script); });
        }
        setIsEngineReady(true);
      } catch (err) {
        console.error("AlaSQL Engine failed to load", err);
      }
    };
    initDB();
  }, []);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (event) => {
      const text = event.target.result;
      const lines = text.split('\n').filter(line => line.trim() !== '');
      if (lines.length < 2) return;

      const headers = lines[0].split(',').map(h => h.trim().replace(/['"]/g, ''));
      const parsedData = lines.slice(1).map(line => {
        const values = line.split(',').map(v => v.trim().replace(/['"]/g, ''));
        const obj = {};
        headers.forEach((header, index) => {
          const val = values[index];
          obj[header] = !isNaN(val) && val !== '' ? Number(val) : val;
        });
        return obj;
      });

      // Load into local SQL Engine
      if (window.alasql) {
        window.alasql(`DROP TABLE IF EXISTS ${TABLE_NAME}`);
        window.alasql(`CREATE TABLE ${TABLE_NAME}`);
        window.alasql(`SELECT * INTO ${TABLE_NAME} FROM ?`, [parsedData]);
      }
      
      // Update schema context so the AI knows what columns exist
      const schemaDescription = `Table Name: ${TABLE_NAME}\nColumns: ${headers.join(', ')}`;
      setSchemaContext(schemaDescription);
      setClarificationTurns(0);

      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'user',
        type: 'system',
        content: `Uploaded dataset: ${file.name} (${parsedData.length} rows, ${headers.length} columns)`
      }]);
    };
    reader.readAsText(file);
    // Reset the input value so the same file can be uploaded again if needed
    e.target.value = '';
  };

  const handleSendMessage = async (textOverride) => {
    const text = textOverride || inputValue;
    if (!text.trim()) return;

    const newUserMsg = { id: Date.now(), role: 'user', type: 'text', content: text };
    setMessages(prev => [...prev, newUserMsg]);
    setInputValue('');
    setIsLoading(true);
    setQueryResults(null);
    setQueryError('');

    try {
      const response = await fetch(BACKEND_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_query: text,
          clarification_turns: clarificationTurns,
          schema_context: schemaContext
        })
      });

      if (!response.ok) throw new Error("Backend connection failed.");
      
      const data = await response.json();

      if (data.status === "SUCCESS") {
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          role: 'assistant',
          type: 'sql_result',
          content: data.summary,
          sql: data.sql
        }]);
        setClarificationTurns(0); // Reset clarification loops on success
      } else {
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          role: 'assistant',
          type: 'text',
          content: data.summary
        }]);
        setClarificationTurns(data.clarification_turns);
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        type: 'text',
        content: `System Error: Unable to reach the Python Backend (${error.message}). Make sure the FastAPI server is running on port 8000.`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const executeSQL = (sql) => {
    try {
      setQueryError('');
      const results = window.alasql(sql);
      setQueryResults(results);
    } catch (err) {
      setQueryError(`Execution Error: ${err.message}`);
      setQueryResults(null);
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans text-slate-800">
      
      {/* Left Sidebar */}
      <div className="w-80 bg-slate-900 text-slate-300 flex flex-col shadow-xl z-10">
        <div className="p-6 border-b border-slate-800">
          <div className="flex items-center gap-3 text-white mb-1">
            <div className="bg-blue-600 p-2 rounded-lg"><Database size={20} /></div>
            <h1 className="text-xl font-bold tracking-tight">Agent DB</h1>
          </div>
          <p className="text-xs text-slate-400">Multi-Agent SQL Knowledge Base</p>
        </div>

        <div className="flex-1 p-4 overflow-y-auto">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4 flex items-center gap-2">
            Preset Ad-Hoc Queries
          </h2>
          <div className="space-y-3">
            {PRESET_QUERIES.map((preset) => (
              <div 
                key={preset.id}
                onClick={() => handleSendMessage(preset.query)}
                className="group relative p-3 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors border border-slate-700 cursor-pointer"
              >
                <div className="flex items-center gap-2 mb-1">
                  <MessageSquare size={14} className="text-blue-400" />
                  <span className="text-sm font-medium text-slate-200 group-hover:text-blue-400 transition-colors">
                    {preset.title}
                  </span>
                </div>
                <p className="text-xs text-slate-500 truncate">{preset.query}</p>
                
                {/* Custom Hover Tooltip */}
                <div className="absolute left-full top-0 ml-2 w-64 p-3 bg-slate-800 border border-slate-700 text-slate-300 text-xs rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 pointer-events-none">
                  <div className="font-semibold text-blue-400 mb-1 flex items-center gap-1">
                    <Info size={12} /> Description
                  </div>
                  {preset.description}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8 pt-4 border-t border-slate-800">
             <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Table size={14} /> Active Schema
            </h2>
            <div className="bg-slate-950 p-3 rounded-lg text-xs font-mono text-emerald-400 whitespace-pre-wrap leading-relaxed border border-slate-800">
              {schemaContext}
            </div>
          </div>
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col bg-white relative">
        
        {/* Chat Header */}
        <header className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-white shadow-sm z-10">
          <div>
            <h2 className="font-semibold text-slate-800">Knowledge Base Chat</h2>
            <p className="text-xs text-slate-500">Powered by LangGraph & Local LLMs</p>
          </div>
          <div className="flex items-center gap-3">
             <span className={`flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full border ${isEngineReady ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
              <span className={`w-2 h-2 rounded-full ${isEngineReady ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`}></span>
              {isEngineReady ? 'Local Engine Ready' : 'Initializing...'}
            </span>
          </div>
        </header>

        {/* Chat Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              
              {/* Avatar Assistant */}
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0 mt-1">
                  <Bot size={18} className="text-blue-600" />
                </div>
              )}

              <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-1' : 'order-2'}`}>
                {/* System Message */}
                {msg.type === 'system' && (
                  <div className="bg-slate-200 text-slate-700 text-xs px-4 py-2 rounded-full flex items-center gap-2">
                    <FileText size={14} /> {msg.content}
                  </div>
                )}

                {/* Text Message */}
                {msg.type === 'text' && (
                  <div className={`p-4 rounded-2xl ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none shadow-sm'}`}>
                    {msg.content}
                  </div>
                )}

                {/* SQL Result Message */}
                {msg.type === 'sql_result' && (
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-none shadow-sm overflow-hidden">
                    <div className="p-4 border-b border-slate-100">
                      <p className="text-sm text-slate-700">{msg.content}</p>
                    </div>
                    <div className="bg-[#1E1E1E] p-4 relative">
                      <p className="text-xs text-slate-500 mb-2 font-mono uppercase tracking-wider">Generated SQL</p>
                      <pre className="text-emerald-400 font-mono text-sm whitespace-pre-wrap">{msg.sql}</pre>
                    </div>
                    
                    <div className="p-3 bg-slate-50 border-t border-slate-200 flex justify-between items-center">
                      <button 
                        onClick={() => executeSQL(msg.sql)}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
                      >
                        <Play size={14} /> Execute Locally
                      </button>
                      
                      {/* Feedback UI */}
                      <div className="flex items-center gap-2 text-slate-400">
                        <span className="text-xs mr-1">Helpful?</span>
                        <button 
                          onClick={() => setFeedbackState(p => ({ ...p, [msg.id]: 'up' }))}
                          className={`p-1.5 rounded hover:bg-slate-200 transition-colors ${feedbackState[msg.id] === 'up' ? 'text-emerald-600 bg-emerald-50' : ''}`}
                        >
                          <ThumbsUp size={16} />
                        </button>
                        <button 
                          onClick={() => setFeedbackState(p => ({ ...p, [msg.id]: 'down' }))}
                          className={`p-1.5 rounded hover:bg-slate-200 transition-colors ${feedbackState[msg.id] === 'down' ? 'text-red-600 bg-red-50' : ''}`}
                        >
                          <ThumbsDown size={16} />
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Avatar User */}
              {msg.role === 'user' && msg.type !== 'system' && (
                <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center shrink-0 order-2 mt-1">
                  <User size={18} className="text-white" />
                </div>
              )}
            </div>
          ))}

          {/* Typing Indicator */}
          {isLoading && (
            <div className="flex gap-4 justify-start">
              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                <Bot size={18} className="text-blue-600" />
              </div>
              <div className="bg-white border border-slate-200 p-4 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-1">
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></span>
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></span>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Floating Results Overlay */}
        {queryResults && (
           <div className="absolute bottom-24 left-6 right-6 bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden z-20 animate-in slide-in-from-bottom-10">
              <div className="px-4 py-3 border-b border-slate-200 flex justify-between items-center bg-slate-50">
                <h3 className="font-semibold text-slate-800 text-sm">Execution Results ({queryResults.length} rows)</h3>
                <button onClick={() => setQueryResults(null)} className="text-slate-400 hover:text-slate-700 bg-slate-200 hover:bg-slate-300 p-1 rounded">
                  <Check size={16} />
                </button>
              </div>
              <div className="max-h-64 overflow-auto">
                {queryResults.length === 0 ? (
                  <div className="p-6 text-center text-sm text-slate-500">No records matched the query criteria.</div>
                ) : (
                  <table className="w-full text-left text-sm">
                    <thead className="bg-white sticky top-0 shadow-sm">
                      <tr>
                        {Object.keys(queryResults[0]).map(k => <th key={k} className="p-3 font-semibold text-slate-600 whitespace-nowrap">{k}</th>)}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {queryResults.slice(0,50).map((r, i) => (
                        <tr key={i} className="hover:bg-slate-50">
                          {Object.values(r).map((v, j) => <td key={j} className="p-3 text-slate-700 whitespace-nowrap">{String(v)}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {queryResults.length > 50 && (
                   <div className="p-2 text-center text-xs text-slate-500 bg-slate-50 border-t border-slate-100">
                     Showing first 50 rows.
                   </div>
                )}
              </div>
           </div>
        )}

        {/* Error Notification */}
        {queryError && (
          <div className="absolute bottom-24 left-6 right-6 bg-red-50 text-red-700 p-4 rounded-xl border border-red-200 flex gap-3 shadow-xl z-20">
            <AlertCircle size={20} className="shrink-0" />
            <p className="text-sm flex-1">{queryError}</p>
            <button onClick={() => setQueryError('')} className="opacity-70 hover:opacity-100"><Check size={16} /></button>
          </div>
        )}

        {/* Chat Input Box */}
        <div className="p-4 bg-white border-t border-slate-200 shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.05)] relative z-30">
          <div className="max-w-4xl mx-auto flex gap-3 items-end">
            
            <input 
              type="file" 
              accept=".csv" 
              ref={fileInputRef} 
              onChange={handleFileUpload}
              className="hidden" 
            />
            
            <button 
              onClick={() => fileInputRef.current?.click()}
              className="p-3 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-colors shrink-0 flex flex-col items-center gap-1 border border-transparent hover:border-blue-100"
              title="Upload Data (CSV)"
            >
              <Upload size={20} />
            </button>

            <div className="flex-1 bg-slate-50 border border-slate-300 rounded-xl flex items-end focus-within:ring-2 focus-within:ring-blue-500/50 focus-within:border-blue-500 overflow-hidden transition-all shadow-sm">
              <textarea 
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder="Ask for a query..."
                className="flex-1 max-h-32 min-h-[52px] p-3.5 bg-transparent resize-none focus:outline-none text-slate-800 text-sm"
                rows={1}
              />
            </div>

            <button 
              onClick={() => handleSendMessage()}
              disabled={!inputValue.trim() || isLoading}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 text-white p-3.5 rounded-xl transition-colors shrink-0 shadow-sm"
            >
              <Send size={18} />
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}