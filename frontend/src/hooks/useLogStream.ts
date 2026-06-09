import { useEffect, useRef, useCallback } from 'react';

export interface LogMessage {
  timestamp: string;
  level: string;
  category: string;
  message: string;
  task_id?: string;
  device_id?: string;
  type?: string;
  [key: string]: unknown;
}

interface UseLogStreamOptions {
  onMessage?: (message: LogMessage) => void;
  onError?: (error: Event) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  level?: string;
  category?: string;
  taskId?: string;
  deviceId?: string;
}

export function useLogStream({
  onMessage,
  onError,
  onConnect,
  onDisconnect,
  level,
  category,
  taskId,
  deviceId,
}: UseLogStreamOptions) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  const buildUrl = useCallback(() => {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8005';
    const url = new URL(`${baseUrl}/api/v1/logs/stream`);
    
    if (level) url.searchParams.set('level', level);
    if (category) url.searchParams.set('category', category);
    if (taskId) url.searchParams.set('task_id', taskId);
    if (deviceId) url.searchParams.set('device_id', deviceId);
    
    return url.toString();
  }, [level, category, taskId, deviceId]);

  const connect = useCallback(() => {
    if (eventSourceRef.current?.readyState === EventSource.OPEN) {
      return;
    }

    const url = buildUrl();
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      reconnectAttemptsRef.current = 0;
      onConnect?.();
    };

    eventSource.onmessage = (event) => {
      try {
        const message: LogMessage = JSON.parse(event.data);
        onMessage?.(message);
      } catch (e) {
        console.error('Failed to parse log message:', e);
      }
    };

    eventSource.onerror = (error) => {
      onError?.(error);
      
      if (eventSource.readyState === EventSource.CLOSED) {
        onDisconnect?.();
        
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          const delay = Math.pow(2, reconnectAttemptsRef.current) * 1000;
          setTimeout(connect, delay);
        }
      }
    };

    eventSourceRef.current = eventSource;
  }, [buildUrl, onMessage, onError, onConnect, onDisconnect]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      onDisconnect?.();
    }
  }, [onDisconnect]);

  const updateParams = useCallback((newParams: Partial<{ level: string; category: string; taskId: string; deviceId: string }>) => {
    disconnect();
    
    if (newParams.level !== undefined) level = newParams.level;
    if (newParams.category !== undefined) category = newParams.category;
    if (newParams.taskId !== undefined) taskId = newParams.taskId;
    if (newParams.deviceId !== undefined) deviceId = newParams.deviceId;
    
    setTimeout(connect, 100);
  }, [connect, disconnect]);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    connect,
    disconnect,
    updateParams,
    isConnected: eventSourceRef.current?.readyState === EventSource.OPEN,
  };
}