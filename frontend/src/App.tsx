import React, { useState, useEffect, useRef } from 'react';
import { useChat, type LeadData } from './hooks/useChat'; 
import { Send, Zap, ShieldCheck, BarChart3, Clock } from 'lucide-react';

export default function App() {
  const [input, setInput] = useState('');
  
  const [leadData, setLeadData] = useState<LeadData>({
    business_segment: null,
    annual_usage_mwh: null,
    contract_status: null,
    months_to_expiry: null,
    building_age: null,
    has_current_provider: null,
    tier: null
  });

  const { messages, sendMessage, isTyping } = useChat(setLeadData);
  const scrollRef = useRef<HTMLDivElement>(null);
  const displayTier = leadData.tier?.replace('LeadTier.TIER_', '') || '--';

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;
    sendMessage(input);
    setInput('');
  };

  return (
    <div className="flex h-screen bg-[#0f172a] text-slate-200 font-sans overflow-hidden">
      
      <div className="w-80 bg-[#1e293b] border-r border-slate-700 p-6 hidden lg:flex flex-col">
        <div className="flex items-center gap-2 mb-10">
          <div className="bg-blue-600 p-2 rounded-lg">
            <Zap className="text-white fill-white" size={20} />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-white italic">ABC ENERGY</h1>
        </div>

        <div className="space-y-6">
          <div>
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
              <BarChart3 size={14} /> Extraction Progress
            </h2>
            <div className="space-y-2">
              {[
                { label: "Segment", value: leadData.business_segment },
                { label: "Usage (MWh)", value: leadData.annual_usage_mwh },
                { label: "Building Age", value: leadData.building_age },
                { label: "Expiry (Mos)", value: leadData.months_to_expiry },
              ].map((item) => (
                <div key={item.label} className="flex justify-between items-center p-3 bg-slate-800/40 rounded-xl border border-slate-700/50 transition-all">
                  <span className="text-sm text-slate-400">{item.label}</span>
                  <span className={`text-xs font-mono ${item.value ? 'text-blue-400 font-bold' : 'text-slate-600'}`}>
                    {item.value ?? '--'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className={`p-5 rounded-2xl border transition-all duration-500 ${leadData.tier ? 'bg-blue-600/20 border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.2)]' : 'bg-slate-900/40 border-slate-800'}`}>
            <h3 className="text-blue-400 text-[10px] font-bold uppercase mb-1 text-center tracking-widest">Lead Priority</h3>
            <p className="text-3xl font-mono text-white text-center font-bold">
              TIER {displayTier}
            </p>
            <p className="text-[10px] text-slate-500 mt-2 italic text-center">
              {leadData.tier ? 'Qualification threshold met' : 'Awaiting dialogue data...'}
            </p>
          </div>
        </div>

        <div className="mt-auto pt-6 border-t border-slate-800 flex items-center gap-3 text-slate-500">
          <Clock size={16} />
          <span className="text-xs font-mono">Session: active</span>
        </div>
      </div>

      
      <div className="flex-1 flex flex-col relative bg-[#0f172a]">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50">
              <ShieldCheck size={48} className="text-slate-700" />
              <div>
                <h3 className="text-lg font-medium text-slate-400">Energy Discovery Mode</h3>
                <p className="text-sm text-slate-600 max-w-xs">Introduce your business to begin qualification.</p>
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
              <div className={`max-w-[80%] px-5 py-3 rounded-2xl whitespace-pre-wrap shadow-lg ${
                m.role === 'user' 
                ? 'bg-blue-600 text-white rounded-br-none' 
                : 'bg-slate-800 text-slate-200 rounded-bl-none border border-slate-700/50'
              }`}>
                <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{m.content}</p>
              </div>
            </div>
          ))}

          {isTyping && (
             <div className="flex justify-start">
               <div className="bg-slate-800/50 border border-slate-700/30 px-4 py-2 rounded-xl text-xs text-slate-500 animate-pulse">
                 AI is analyzing lead data...
               </div>
             </div>
          )}
        </div>

        
        <div className="p-6 bg-[#0f172a] border-t border-slate-800/50">
          <form onSubmit={handleSend} className="max-w-4xl mx-auto flex gap-3 p-2 bg-[#1e293b] border border-slate-700 rounded-2xl focus-within:border-blue-500/50 transition-all shadow-2xl">
            <input
              className="flex-1 bg-transparent px-4 py-2 focus:outline-none text-white placeholder-slate-500"
              placeholder="e.g., I'm with a manufacturing plant using 800MWh..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button 
              type="submit" 
              disabled={isTyping || !input.trim()}
              className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white p-3 rounded-xl transition-all active:scale-95"
            >
              <Send size={20} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}