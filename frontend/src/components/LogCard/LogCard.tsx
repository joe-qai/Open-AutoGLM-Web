import { Bot, Play, CheckCircle2, AlertCircle, Clock, Lightbulb } from 'lucide-react';

export interface LogEntry {
  id: string;
  step: number;
  type: 'system' | 'think' | 'action' | 'success' | 'error' | 'warning';
  action?: string;
  thinking?: string;
  result?: string;
  timestamp: Date;
}

interface LogCardProps {
  log: LogEntry;
}

export function LogCard({ log }: LogCardProps) {
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
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {getIcon()}
          {getStepBadge()}
          <span className="text-xs text-gray-500">{formatTime(log.timestamp)}</span>
        </div>
        {log.action && (
          <span className="px-2 py-0.5 text-xs font-semibold bg-white/80 rounded-md text-gray-700 shadow-sm">
            {log.action}
          </span>
        )}
      </div>

      {/* Thinking content */}
      {log.thinking && (
        <div className="bg-white rounded-lg p-3 shadow-sm mb-2">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
            <span className="text-xs font-medium text-amber-700">思考过程</span>
          </div>
          <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {log.thinking}
          </p>
        </div>
      )}

      {/* Result content */}
      {log.result && (
        <div className={`rounded-lg p-3 ${log.type === 'error' ? 'bg-red-100' : 'bg-white'} shadow-sm`}>
          <p className={`text-sm ${log.type === 'error' ? 'text-red-700' : 'text-gray-700'} whitespace-pre-wrap`}>
            {log.result}
          </p>
        </div>
      )}

      {/* Simple message */}
      {!log.thinking && !log.result && (
        <p className="text-sm text-gray-700">{log.action || log.thinking}</p>
      )}
    </div>
  );
}
