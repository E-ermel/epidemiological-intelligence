"use client";

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ObservedVsPredictedPoint } from "@/types/model";
import { formatMonth, formatNumber } from "@/lib/utils";

export function ObservedVsPredictedChart({ data }: { data: ObservedVsPredictedPoint[] }) {
  // The API doesn't guarantee ordering, and the real test period is
  // long enough (unlike the old 6-point mock) that a fixed interval=0
  // tick for every point makes the axis unreadable -- preserveStartEnd
  // + minTickGap lets Recharts space ticks out like EpidemiologicalChart
  // already does for the (much longer) case curve.
  const sortedData = [...data].sort((a, b) =>
    a.referenceDate.localeCompare(b.referenceDate)
  );

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={sortedData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--color-border)" />

        <XAxis
          dataKey="referenceDate"
          tickFormatter={(value: string) => formatMonth(value)}
          tick={{ fontSize: 12, fill: "var(--color-muted)" }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
          minTickGap={24}
        />

        <YAxis
          tick={{ fontSize: 12, fill: "var(--color-muted)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(value: number) => formatNumber(value)}
          width={40}
        />

        <Tooltip
          labelFormatter={(value) => formatMonth(String(value))}
          contentStyle={{
            borderRadius: 12,
            border: "1px solid var(--color-border)",
            boxShadow: "var(--shadow-card)",
            fontSize: 13,
          }}
        />

        <Legend
          verticalAlign="top"
          height={32}
          iconType="circle"
          formatter={(value) => (
            <span className="text-xs text-muted">{value}</span>
          )}
        />

        <Line
          type="monotone"
          dataKey="observedCases"
          name="Observado"
          stroke="var(--color-foreground)"
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="predictedCases"
          name="Previsto"
          stroke="var(--color-primary-600)"
          strokeWidth={2}
          strokeDasharray="4 4"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
