/**
 * 与 FastAPI / Pydantic 序列化一致：字段名使用 snake_case，日期为 ISO 字符串。
 */

export type LoginRequest = {
  username: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type SessionCreate = {
  title?: string | null;
};

export type SessionUpdate = {
  title: string;
};

export type SessionOut = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type MessageCreate = {
  content: string;
};

export type ChartDataJson = {
  columns: string[];
  rows: unknown[][];
};

/** 助手消息的 meta_json 解析结果（与后端写入结构一致） */
export type AssistantMessageMeta = {
  sql?: string | null;
  data?: ChartDataJson;
  meta?: Record<string, unknown>;
};

export type MessageOut = {
  id: number;
  role: string;
  content: string;
  meta?: AssistantMessageMeta | null;
};

export type ChatResponse = {
  reply: string;
  sql: string | null;
  data: ChartDataJson;
  meta: Record<string, unknown>;
};
