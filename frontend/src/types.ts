export type Role = "user" | "assistant";

/** 界面消息：id 为稳定字符串（服务端消息用 `m-{id}`） */
export type Message = {
  id: string;
  role: Role;
  content: string;
  createdAt: number;
  /** 来自助手消息 meta.sql */
  sql?: string | null;
};

export type Session = {
  id: string;
  title: string;
  updatedAt: number;
};

export type ChartPayload = {
  categories: string[];
  values: number[];
  title: string;
};

/** 与后端 data.columns / data.rows 对齐，供表格 Tab 使用 */
export type QueryTablePayload = {
  columns: string[];
  rows: unknown[][];
};
