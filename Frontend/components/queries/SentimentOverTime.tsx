"use client";

import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
  type ChartOptions,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { SENTIMENT_STYLE } from "@/components/ui";
import { formatShortDate } from "@/lib/format";
import { SENTIMENTS, type Dashboard } from "@/lib/types";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

const AXIS = { color: "#5E6A75", font: { family: "Inter, system-ui, sans-serif", size: 12 } };

/** Posts per day for each class: 3 lines, no event markers (plan §8.5). */
export default function SentimentOverTime({ perDay }: { perDay: Dashboard["per_day"] }) {
  const data = {
    labels: perDay.map((d) => formatShortDate(d.date)),
    datasets: SENTIMENTS.map((s) => ({
      label: SENTIMENT_STYLE[s].label,
      data: perDay.map((d) => d[s]),
      borderColor: SENTIMENT_STYLE[s].hex,
      backgroundColor: SENTIMENT_STYLE[s].hex,
      borderWidth: 2,
      pointRadius: perDay.length > 30 ? 0 : 3,
      pointHoverRadius: 5,
      cubicInterpolationMode: "monotone" as const,
    })),
  };

  const options: ChartOptions<"line"> = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false, // calm, static charts (DESIGN.md)
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { position: "bottom", align: "start", labels: { ...AXIS, boxWidth: 10, boxHeight: 10, usePointStyle: true, pointStyle: "rect", padding: 18 } },
      tooltip: {
        backgroundColor: "#FFFFFF",
        borderColor: "#E2DCD0",
        borderWidth: 1,
        titleColor: "#172B3A",
        bodyColor: "#334155",
        padding: 12,
        titleFont: { family: "Inter, system-ui, sans-serif", weight: 600 },
        bodyFont: { family: "Inter, system-ui, sans-serif" },
        boxPadding: 4,
      },
    },
    scales: {
      x: { grid: { display: false }, border: { color: "#E2DCD0" }, ticks: { ...AXIS, maxRotation: 0, autoSkipPadding: 16 } },
      y: { beginAtZero: true, grid: { color: "#EEE9DF" }, border: { display: false }, ticks: { ...AXIS, precision: 0 }, title: { display: true, text: "Posts", ...AXIS } },
    },
  };

  return (
    <div className="h-[280px] sm:h-[320px]" role="img" aria-label="Line chart of positive, neutral and negative posts per day">
      <Line data={data} options={options} />
    </div>
  );
}
