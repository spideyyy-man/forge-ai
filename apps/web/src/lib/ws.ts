import { WSMessage } from "@/types";

type MessageHandler = (message: WSMessage) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string = "";
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 10;
  private reconnectInterval: number = 2000;
  private handlers: Set<MessageHandler> = new Set();
  private isExplicitlyClosed: boolean = false;

  connect(userId: string) {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const host = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/user";
    this.url = `${host}/${userId}`;
    this.isExplicitlyClosed = false;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log("[Forge WS] Connected to user stream");
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const parsed: WSMessage = JSON.parse(event.data);
          this.handlers.forEach((handler) => handler(parsed));
        } catch (err) {
          console.error("[Forge WS] Error parsing message:", err);
        }
      };

      this.ws.onclose = () => {
        if (!this.isExplicitlyClosed) {
          console.log("[Forge WS] Disconnected, scheduling reconnect...");
          this.scheduleReconnect(userId);
        }
      };

      this.ws.onerror = (error) => {
        console.error("[Forge WS] Error:", error);
      };
    } catch (e) {
      console.error("[Forge WS] Failed to initiate connection:", e);
      this.scheduleReconnect(userId);
    }
  }

  private scheduleReconnect(userId: string) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const timeout = this.reconnectInterval * Math.min(this.reconnectAttempts, 5);
      setTimeout(() => {
        if (!this.isExplicitlyClosed) {
          this.connect(userId);
        }
      }, timeout);
    }
  }

  send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn("[Forge WS] Cannot send, socket not open");
    }
  }

  subscribe(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  disconnect() {
    this.isExplicitlyClosed = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.handlers.clear();
  }
}

export const wsClient = new WebSocketClient();
