import http from "./http";

export type ChatRoute = "knowledge" | "recommend" | "report" | "profile_update" | "help" | "blocked";

export interface ChatSource {
  chunk_id: string;
  source: string;
  page: number;
}

export interface ChatReply {
  session_id: number;
  route: ChatRoute;
  blocked: boolean;
  answer: string;
  citation_ids: string[];
  sources: ChatSource[];
  graph: string;
  rag: string;
  pending_profile_id: number | null;
  draft: { allergies?: string[]; dislikes?: string[] };
}

export interface ChatSessionSummary {
  id: number;
  preview: string;
}

export interface ChatMessageView {
  id: number;
  role: string;
  content: string;
  meta: {
    route?: ChatRoute;
    blocked?: boolean;
    sources?: ChatSource[];
    pending_profile_id?: number | null;
    draft?: { allergies?: string[]; dislikes?: string[] };
  };
}

export interface ChatStreamHandlers {
  onToken: (text: string) => void;
  onSources: (items: ChatSource[]) => void;
  onPending: (pendingId: number, draft: ChatReply["draft"]) => void;
  onDone: (sessionId: number, route: ChatRoute) => void;
}

export function fetchSessions() {
  return http.get<ChatSessionSummary[]>("/api/v1/chat/sessions");
}

export function fetchSession(sessionId: number) {
  return http.get<{ id: number; messages: ChatMessageView[] }>(`/api/v1/chat/sessions/${sessionId}`);
}

export async function streamChat(
  message: string,
  sessionId: number | null,
  handlers: ChatStreamHandlers,
): Promise<void> {
  const token = localStorage.getItem("tangan.token") ?? "";
  const response = await fetch("/api/v1/chat/stream", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (response.status === 401) {
    throw new Error("unauthorized");
  }
  if (!response.ok || response.body == null) {
    throw new Error("chat_failed");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) {
        continue;
      }
      const event = JSON.parse(line) as {
        event?: string;
        text?: string;
        items?: ChatSource[];
        pending_profile_id?: number;
        draft?: ChatReply["draft"];
        session_id?: number;
        route?: ChatRoute;
      };
      if (event.event === "token" && event.text) {
        handlers.onToken(event.text);
      } else if (event.event === "sources" && event.items) {
        handlers.onSources(event.items);
      } else if (event.event === "profile_pending" && event.pending_profile_id != null) {
        handlers.onPending(event.pending_profile_id, event.draft ?? {});
      } else if (event.event === "done" && event.session_id != null && event.route) {
        handlers.onDone(event.session_id, event.route);
      }
    }
    if (done) {
      break;
    }
  }
}
