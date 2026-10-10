import { useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import ReactECharts from "echarts-for-react";
import { useWorkspace } from "./WorkspaceContext";

type VizTab = "bar" | "pie" | "line" | "table";

const TABS: { id: VizTab; label: string }[] = [
  { id: "bar", label: "柱状图" },
  { id: "pie", label: "饼图" },
  { id: "line", label: "折线图" },
  { id: "table", label: "表格" },
];

const PALETTE = [
  "#22d3ee",
  "#a78bfa",
  "#34d399",
  "#f472b6",
  "#fb923c",
  "#38bdf8",
  "#fcd34d",
  "#2dd4bf",
];

const AXIS = "#64748b";
const SPLIT = "rgba(148, 163, 184, 0.12)";
const TEXT = "#94a3b8";

function cellStr(v: unknown): string {
  if (v === null || v === undefined) return "";
  return String(v);
}

export function ChartPanel() {
  const { chart, tableData } = useWorkspace();
  const [tab, setTab] = useState<VizTab>("bar");

  const pieSeriesData = useMemo(
    () =>
      chart.categories.map((name, i) => ({
        name,
        value: chart.values[i] ?? 0,
      })),
    [chart.categories, chart.values],
  );

  const barOption = useMemo<EChartsOption>(
    () => ({
      backgroundColor: "transparent",
      title: {
        text: chart.title,
        left: "center",
        textStyle: { fontSize: 13, fontWeight: 600, color: TEXT },
      },
      grid: { left: 52, right: 20, top: 44, bottom: 28 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 23, 42, 0.92)",
        borderColor: "rgba(34, 211, 238, 0.35)",
        textStyle: { color: "#e2e8f0", fontSize: 12 },
      },
      xAxis: {
        type: "category",
        data: chart.categories,
        axisLine: { lineStyle: { color: AXIS } },
        axisLabel: { color: TEXT, fontSize: 11 },
      },
      yAxis: {
        type: "value",
        axisLine: { show: false },
        axisLabel: { color: TEXT, fontSize: 11 },
        splitLine: { lineStyle: { color: SPLIT } },
      },
      series: [
        {
          type: "bar",
          data: chart.values.map((v, i) => ({
            value: v,
            itemStyle: {
              color: {
                type: "linear",
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: PALETTE[i % PALETTE.length] },
                  { offset: 1, color: "rgba(15, 23, 42, 0.4)" },
                ],
              },
              borderRadius: [6, 6, 0, 0],
            },
          })),
        },
      ],
    }),
    [chart],
  );

  const lineOption = useMemo<EChartsOption>(
    () => ({
      backgroundColor: "transparent",
      title: {
        text: chart.title,
        left: "center",
        textStyle: { fontSize: 13, fontWeight: 600, color: TEXT },
      },
      grid: { left: 52, right: 20, top: 44, bottom: 28 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15, 23, 42, 0.92)",
        borderColor: "rgba(34, 211, 238, 0.35)",
        textStyle: { color: "#e2e8f0", fontSize: 12 },
      },
      xAxis: {
        type: "category",
        data: chart.categories,
        boundaryGap: false,
        axisLine: { lineStyle: { color: AXIS } },
        axisLabel: { color: TEXT, fontSize: 11 },
      },
      yAxis: {
        type: "value",
        axisLine: { show: false },
        axisLabel: { color: TEXT, fontSize: 11 },
        splitLine: { lineStyle: { color: SPLIT } },
      },
      series: [
        {
          type: "line",
          data: chart.values,
          smooth: true,
          symbol: "circle",
          symbolSize: 8,
          lineStyle: { width: 2, color: "#22d3ee" },
          itemStyle: { color: "#67e8f9", borderColor: "#0e7490", borderWidth: 1 },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(34, 211, 238, 0.35)" },
                { offset: 1, color: "rgba(34, 211, 238, 0.02)" },
              ],
            },
          },
        },
      ],
    }),
    [chart],
  );

  const pieOption = useMemo<EChartsOption>(
    () => ({
      backgroundColor: "transparent",
      title: {
        text: chart.title,
        left: "center",
        top: 8,
        textStyle: { fontSize: 13, fontWeight: 600, color: TEXT },
      },
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(15, 23, 42, 0.92)",
        borderColor: "rgba(167, 139, 250, 0.35)",
        textStyle: { color: "#e2e8f0", fontSize: 12 },
      },
      legend: {
        bottom: 4,
        textStyle: { color: TEXT, fontSize: 10 },
        type: "scroll",
      },
      series: [
        {
          type: "pie",
          radius: ["36%", "62%"],
          center: ["50%", "52%"],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 6,
            borderColor: "rgba(15, 23, 42, 0.9)",
            borderWidth: 2,
          },
          label: { color: TEXT, fontSize: 11 },
          data: pieSeriesData.map((d, i) => ({
            ...d,
            itemStyle: { color: PALETTE[i % PALETTE.length] },
          })),
        },
      ],
    }),
    [chart.title, pieSeriesData],
  );

  const chartOption =
    tab === "bar" ? barOption : tab === "line" ? lineOption : pieOption;

  return (
    <section className="panel chart-panel">
      <div className="panel-header">
        <h2>数据视图</h2>
        <span className="badge badge--glow">多视图</span>
      </div>
      <div className="viz-tabs" role="tablist" aria-label="图表类型">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`viz-tab${tab === t.id ? " viz-tab--active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="viz-body">
        {tab === "table" ? (
          <div className="viz-table-wrap">
            {tableData && tableData.columns.length > 0 ? (
              <table className="viz-table">
                <thead>
                  <tr>
                    {tableData.columns.map((c) => (
                      <th key={c}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {tableData.rows.map((row, ri) => (
                    <tr key={ri}>
                      {tableData.columns.map((_, ci) => (
                        <td key={ci}>{cellStr(row[ci])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="viz-table-empty">
                暂无原始表格数据。发起 NL2SQL 查询后，此处展示后端返回的列与行。
              </p>
            )}
          </div>
        ) : (
          <div className="chart-wrap chart-wrap--viz">
            <ReactECharts
              key={tab}
              option={chartOption}
              style={{ height: "100%", minHeight: 300 }}
              opts={{ renderer: "canvas" }}
            />
          </div>
        )}
      </div>
    </section>
  );
}
