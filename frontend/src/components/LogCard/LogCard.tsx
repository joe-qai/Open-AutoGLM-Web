import { useState } from 'react';
import { Bot, Play, CheckCircle2, AlertCircle, Clock, Lightbulb, Image, ChevronDown, ChevronUp } from 'lucide-react';

export interface LogEntry {
  id: string;
  step: number;
  type: 'system' | 'think' | 'action' | 'success' | 'error' | 'warning';
  action?: string;
  thinking?: string;
  thinkingAction?: string;
  result?: string;
  screenshot?: string;  // base64 截图
  timestamp: Date;
}

interface LogCardProps {
  log: LogEntry;
  onImageClick?: (screenshot: string) => void;
}

export function LogCard({ log }: LogCardProps) {
  const [imageExpanded, setImageExpanded] = useState(false);

  const getIcon = () => {
    switch (log.type) {
      case 'system':
        return <Bot className="w-4 h-4 text-blue-500" />;
      case 'think':
        return <Lightbulb className="w-4 h-4 text-amber-500" />;
      case 'action':
        return <Play className="w-4 h-4 text-green-500" />;
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'warning':
        return <Clock className="w-4 h-4 text-orange-500" />;
      default:
        return <Bot className="w-4 h-4 text-gray-400" />;
    }
  };

  const getBorderColor = () => {
    switch (log.type) {
      case 'system':
        return 'border-l-blue-500';
      case 'think':
        return 'border-l-amber-500';
      case 'action':
        return 'border-l-green-500';
      case 'success':
        return 'border-l-emerald-500';
      case 'error':
        return 'border-l-red-500';
      case 'warning':
        return 'border-l-orange-500';
      default:
        return 'border-l-gray-400';
    }
  };

  const getBgColor = () => {
    switch (log.type) {
      case 'system':
        return 'bg-blue-50/50';
      case 'think':
        return 'bg-amber-50/50';
      case 'action':
        return 'bg-green-50/50';
      case 'success':
        return 'bg-emerald-50/50';
      case 'error':
        return 'bg-red-50/50';
      case 'warning':
        return 'bg-orange-50/50';
      default:
        return 'bg-gray-50/50';
    }
  };

  const getStepBadge = () => {
    if (log.step > 0) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
          Step {log.step}
        </span>
      );
    }
    return null;
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  return (
    <div
      className={`relative pl-4 border-l-2 ${getBorderColor()} ${getBgColor()} rounded-r-lg p-3 mb-2 transition-all duration-300 hover:shadow-sm`}
    >
      {/* Header: step badge + time + action label */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {getIcon()}
          {getStepBadge()}
          <span className="text-xs text-gray-500">{formatTime(log.timestamp)}</span>
        </div>
        {log.action && (
          <span className={`px-2 py-0.5 text-xs font-semibold bg-white/80 rounded-md shadow-sm ${
            log.type === 'warning' ? 'text-orange-700' : 'text-gray-700'
          }`}>
            {log.action}
          </span>
        )}
      </div>

      {/* Thinking content (merged from think+act) */}
      {log.thinking && (
        <div className="bg-white/80 rounded-lg p-3 shadow-sm mb-2">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
            <span className="text-xs font-medium text-amber-700">思考过程</span>
          </div>
          <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {log.thinking}
          </p>
        </div>
      )}

      {/* Result content (action result or error) */}
      {log.result && (
        <div className={`rounded-lg p-3 shadow-sm ${
          log.result.includes('[NOTE:') 
            ? 'bg-orange-50 border border-orange-200'
            : log.type === 'error' ? 'bg-red-100' : 'bg-white'
        }`}>
          <p className={`text-sm whitespace-pre-wrap ${
            log.result.includes('[NOTE:') 
              ? 'text-orange-700 font-medium'
              : log.type === 'error' ? 'text-red-700' : 'text-gray-700'
          }`}>
            {log.result}
          </p>
        </div>
      )}

      {/* Screenshot preview - collapsible */}
      {log.screenshot && (
        <div className="mt-2 rounded-lg overflow-hidden border border-gray-200 bg-white shadow-sm">
          <button
            onClick={() => setImageExpanded(!imageExpanded)}
            className="w-full flex items-center justify-between px-3 py-1.5 bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200 hover:from-gray-100 hover:to-gray-200 transition-all"
          >
            <div className="flex items-center gap-1.5">
              <Image className="w-3.5 h-3.5 text-gray-500" />
              <span className="text-xs font-medium text-gray-600">屏幕截图</span>
              <span className="text-xs text-gray-400">点击展开/收起</span>
            </div>
            {imageExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>
          <div className={`overflow-hidden transition-all duration-300 ${imageExpanded ? 'max-h-[500px]' : 'max-h-24'}`}>
            <div className="p-2">
              <img 
                src={`data:image/png;base64,${log.screenshot}`}
                alt="设备屏幕截图"
                className={`w-full h-auto rounded-lg object-contain transition-all duration-300 ${
                  imageExpanded ? 'max-h-[450px]' : 'max-h-20'
                } cursor-pointer hover:ring-2 hover:ring-blue-300 hover:ring-offset-1`}
                onClick={() => {
                  // 点击放大显示
                  const img = new window.Image();
                  img.src = `data:image/png;base64,${log.screenshot}`;
                  const win = window.open('', '_blank');
                  if (win) {
                    win.document.write(`<html><head><title>屏幕截图 - Step ${log.step}</title><style>body{margin:0;background:#1a1a1a;display:flex;justify-content:center;align-items:center;min-height:100vh}</style></head><body><img src="data:image/png;base64,${log.screenshot}" style="max-width:95vw;max-height:95vh;box-shadow:0 0 30px rgba(0,0,0,0.5)"/></body></html>`);
                    win.document.close();
                  }
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Simple message */}
      {!log.thinking && !log.result && !log.screenshot && (
        <p className="text-sm text-gray-700">{log.action || log.thinking}</p>
      )}
    </div>
  );
}
