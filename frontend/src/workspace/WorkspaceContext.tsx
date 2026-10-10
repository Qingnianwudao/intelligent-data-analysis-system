import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ApiError, createSession as apiCreateSession, deleteSession as apiDeleteSession, listMessages, listSessions, postMessage, updateSession } from "../api/client";
import type { MessageOut, SessionOut } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import type { ChartPayload, Message, QueryTablePayload, Session } from "../types";
import { emptyViz, vizFromQueryData } from "../lib/chartFromQueryData";

type WorkspaceContextValue = {
  sessions: Session[];
  currentSessionId: string | null;
  messages: Message[];
  chart: ChartPayload;
  /** 后端原始行列，表格 Tab 使用；无查询结果时为 null */
  tableData: QueryTablePayload | null;
  selectSession: (id: string) => Promise<void>;
  createSession: () => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  sendMessage: (text: string) => Promise<void>;
  loading: boolean;
  sending: boolean;
  error: string | null;
  clearError: () => void;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

function sessionToUi(s: SessionOut): Session {
  const t = Date.parse(s.updated_at);
  return {
    id: s.id,
    title: s.title,
    updatedAt: Number.isFinite(t) ? t : Date.now(),
  };
}

function messageToUi(m: MessageOut): Message {
  const meta = m.meta;
  return {
    id: `m-${m.id}`,
    role: m.role === "user" ? "user" : "assistant",
    content: m.content,
    createdAt: Date.now(),
    sql: meta?.sql ?? null,
  };
}

function vizFromMessages(msgs: MessageOut[]) {
  for (let i = msgs.length - 1; i >= 0; i--) {
    const m = msgs[i];
    if (m.role !== "assistant") continue;
    const data = m.meta?.data;
    if (data?.columns?.length && data.rows?.length) {
      return vizFromQueryData(data.columns, data.rows, "查询结果");
    }
  }
  return emptyViz();
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { token, logout } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [chart, setChart] = useState<ChartPayload>(() => emptyViz().chart);
  const [tableData, setTableData] = useState<QueryTablePayload | null>(
    () => emptyViz().table,
  );
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const handleApiFailure = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError && e.status === 401) {
        logout();
        setError("登录已失效，请重新登录");
        return;
      }
      const msg = e instanceof Error ? e.message : "请求失败";
      setError(msg);
    },
    [logout],
  );

  const applySessionList = useCallback((list: SessionOut[], preferredId: string | null) => {
    const ui = list.map(sessionToUi);
    setSessions(ui);
    const pick =
      preferredId && ui.some((s) => s.id === preferredId)
        ? preferredId
        : ui[0]?.id ?? null;
    setCurrentSessionId(pick);
    return pick;
  }, []);

  const loadMessagesFor = useCallback(
    async (sid: string) => {
      if (!token) return;
      const msgs = await listMessages(token, sid);
      setMessages(msgs.map(messageToUi));
      const v = vizFromMessages(msgs);
      setChart(v.chart);
      setTableData(v.table);
    },
    [token],
  );

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    (async () => {
      setLoading(true);
      setError(null);
      try {
        let list = await listSessions(token);
        if (cancelled) return;
        if (list.length === 0) {
          const created = await apiCreateSession(token, {});
          if (cancelled) return;
          list = [created];
        }
        const pick = applySessionList(list, list[0]?.id ?? null);
        if (pick) await loadMessagesFor(pick);
      } catch (e) {
        if (!cancelled) handleApiFailure(e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [token, applySessionList, loadMessagesFor, handleApiFailure]);

  const selectSession = useCallback(
    async (id: string) => {
      if (!token) return;
      setCurrentSessionId(id);
      setError(null);
      try {
        await loadMessagesFor(id);
      } catch (e) {
        handleApiFailure(e);
      }
    },
    [token, loadMessagesFor, handleApiFailure],
  );

  const createSession = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      const created = await apiCreateSession(token, {});
      const list = await listSessions(token);
      applySessionList(list, created.id);
      setMessages([]);
      const ev = emptyViz();
      setChart(ev.chart);
      setTableData(ev.table);
    } catch (e) {
      handleApiFailure(e);
    }
  }, [token, applySessionList, handleApiFailure]);

  const deleteSession = useCallback(
    async (id: string) => {
      if (!token) return;
      setError(null);
      try {
        await apiDeleteSession(token, id);
        let list = await listSessions(token);
        if (list.length === 0) {
          const created = await apiCreateSession(token, {});
          list = [created];
        }
        const nextId =
          currentSessionId === id ? list[0]?.id ?? null : currentSessionId;
        applySessionList(list, nextId);
        if (nextId) await loadMessagesFor(nextId);
      } catch (e) {
        handleApiFailure(e);
      }
    },
    [token, currentSessionId, applySessionList, loadMessagesFor, handleApiFailure],
  );

  const sendMessage = useCallback(
    async (text: string) => {
      if (!token || !currentSessionId) return;
      const trimmed = text.trim();
      if (!trimmed) return;

      setSending(true);
      setError(null);
      try {
        const sessionRow = sessions.find((s) => s.id === currentSessionId);
        if (sessionRow?.title === "新会话") {
          const nextTitle = trimmed.slice(0, 24) || "新会话";
          await updateSession(token, currentSessionId, { title: nextTitle });
        }

        const chat = await postMessage(token, currentSessionId, {
          content: trimmed,
        });

        const list = await listSessions(token);
        applySessionList(list, currentSessionId);
        const msgs = await listMessages(token, currentSessionId);
        setMessages(msgs.map(messageToUi));

        const cols = chat.data?.columns ?? [];
        const rows = chat.data?.rows ?? [];
        const v = vizFromQueryData(cols, rows, "查询结果");
        setChart(v.chart);
        setTableData(v.table);
      } catch (e) {
        handleApiFailure(e);
      } finally {
        setSending(false);
      }
    },
    [token, currentSessionId, sessions, applySessionList, handleApiFailure],
  );

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      sessions,
      currentSessionId,
      messages,
      chart,
      tableData,
      selectSession,
      createSession,
      deleteSession,
      sendMessage,
      loading,
      sending,
      error,
      clearError,
    }),
    [
      sessions,
      currentSessionId,
      messages,
      chart,
      tableData,
      selectSession,
      createSession,
      deleteSession,
      sendMessage,
      loading,
      sending,
      error,
      clearError,
    ],
  );

  return (
    <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return ctx;
}
