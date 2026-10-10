import type { ChartPayload, QueryTablePayload } from "../types";

function toNum(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "boolean") return v ? 1 : 0;
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function stringifyCell(v: unknown): string {
  if (v === null || v === undefined) return "";
  return String(v);
}

export type VizBundle = {
  chart: ChartPayload;
  table: QueryTablePayload | null;
};

/** 将后端 `data.columns` / `data.rows` 转为柱状图所需 categories / values */
export function chartFromQueryData(
  columns: string[],
  rows: unknown[][],
  title = "查询结果",
): ChartPayload {
  if (!columns.length || !rows.length) {
    return {
      categories: ["—"],
      values: [0],
      title: title.trim() || "暂无数据",
    };
  }

  const numericScore = (col: number) =>
    rows.filter((r) => toNum(r[col]) !== null).length;

  let valIdx = 0;
  let best = -1;
  for (let i = 0; i < columns.length; i++) {
    const s = numericScore(i);
    if (s > best) {
      best = s;
      valIdx = i;
    }
  }

  let catIdx = columns.findIndex((_, i) => i !== valIdx);
  if (catIdx < 0) catIdx = -1;

  const categories =
    catIdx >= 0
      ? rows.map((r) => stringifyCell(r[catIdx]))
      : rows.map((_, i) => `第 ${i + 1} 行`);

  const values = rows.map((r) => toNum(r[valIdx]) ?? 0);

  return { categories, values, title: title.trim() || "查询结果" };
}

export function vizFromQueryData(
  columns: string[],
  rows: unknown[][],
  title = "查询结果",
): VizBundle {
  const chart = chartFromQueryData(columns, rows, title);
  const hasGrid = columns.length > 0 && rows.length > 0;
  return {
    chart,
    table: hasGrid ? { columns, rows } : null,
  };
}

export function emptyChart(): ChartPayload {
  return {
    categories: ["一月", "二月", "三月"],
    values: [12, 19, 15],
    title: "示例：连接后端后将显示真实查询结果",
  };
}

export function emptyViz(): VizBundle {
  return { chart: emptyChart(), table: null };
}
