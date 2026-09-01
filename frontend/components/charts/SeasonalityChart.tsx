"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SeasonalAggregate } from "@/lib/aggregateEpidemiologicalRecords";
import { formatNumber } from "@/lib/utils";

const MONTH_LABELS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

export function SeasonalityChart({ data }: { data: SeasonalAggregate[] }) {
  const chartData = data.map((point) => ({
    ...point,
    label: MONTH_LABELS[point.month - 1],
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--color-border)" />

        <XAxis
          dataKey="label"
          tick={{ fontSize: 12, fill: "var(--color-muted)" }}
          axisLine={false}
          tickLine={false}
        />

        <YAxis
          tick={{ fontSize: 12, fill: "var(--color-muted)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(value: number) => formatNumber(Math.round(value))}
          width={48}
        />

        <Tooltip
          formatter={(value) => [formatNumber(Math.round(Number(value))), "Média de casos"]}
          contentStyle={{
            borderRadius: 12,
            border: "1px solid var(--color-border)",
            boxShadow: "var(--shadow-card)",
            fontSize: 13,
          }}
        />

        <Bar dataKey="avgCases" fill="var(--color-primary-500)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
