import { useEffect, useRef, useCallback } from 'react';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export const useWebSocket = (
  onMessage: (data: WebSocketMessage) => void,
  onConnect?: () => void,
  onDisconnect?: () => void
) => {
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/ws';

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      onConnect?.();

      // Subscribe to sensor updates
      ws.current?.send(JSON.stringify({
        type: 'subscribe',
        topics: ['sensor_update', 'server_status']
      }));
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
      onDisconnect?.();

      // Reconnect after 5 seconds
      reconnectTimeout.current = setTimeout(() => {
        connect();
      }, 5000);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }, [onMessage, onConnect, onDisconnect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
    ws.current?.close();
  }, []);

  const send = useCallback((data: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return { send, disconnect };
};
