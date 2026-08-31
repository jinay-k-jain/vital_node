/**
 * VitalNode WebSocket client.
 * Connects to the backend queue WebSocket and pushes
 * live updates into the Zustand store automatically.
 */

const WS_URL = (import.meta.env.VITE_WS_URL as string) || 'ws://localhost:8000/api/v1/ws/queue';

let _socket: WebSocket | null = null;
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let _onQueueUpdate: ((data: any[]) => void) | null = null;

export function setQueueUpdateHandler(handler: (queue: any[]) => void) {
  _onQueueUpdate = handler;
}

export function connectQueueSocket() {
  if (_socket && _socket.readyState === WebSocket.OPEN) return;

  _socket = new WebSocket(WS_URL);

  _socket.onopen = () => {
    console.log('[WS] Queue socket connected');
    if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }
  };

  _socket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === 'QUEUE_UPDATE' && Array.isArray(msg.queue)) {
        _onQueueUpdate?.(msg.queue);
      }
    } catch {
      // ignore parse errors
    }
  };

  _socket.onclose = () => {
    console.log('[WS] Queue socket closed — reconnecting in 5s');
    _socket = null;
    _reconnectTimer = setTimeout(connectQueueSocket, 5000);
  };

  _socket.onerror = () => {
    _socket?.close();
  };

  // Send keepalive ping every 25 seconds
  const pingInterval = setInterval(() => {
    if (_socket?.readyState === WebSocket.OPEN) {
      _socket.send('ping');
    } else {
      clearInterval(pingInterval);
    }
  }, 25000);
}

export function disconnectQueueSocket() {
  if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }
  _socket?.close();
  _socket = null;
}
