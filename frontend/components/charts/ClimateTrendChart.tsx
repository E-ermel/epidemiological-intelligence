"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MonthlyAggregate } from "@/lib/aggregateEpidemiologicalRecords";
import { formatMonth, formatNumber } from "@/lib/utils";

export function ClimateTrendChart({
  data,
  variableLabel,
}: {
  data: MonthlyAggregate[];
  variableLabel: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="climateCasesFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-primary-500)" stopOpacity={0.2} />
            <stop offset="100%" stopColor="var(--color-primary-500)" stopOpacity={0} />
          </linearGradient>
        </defs>

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
          yAxisId="cases"
          tick={{ fontSize: 12, fill: "var(--color-muted)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(value: number) => formatNumber(value)}
          width={48}
        />

        <YAxis
          yAxisId="climate"
          orientation="right"
          tick={{ fontSize: 12, fill: "var(--color-muted-light)" }}
          axisLine={false}
          tickLine={false}
          width={48}
        />

        <Tooltip
          labelFormatter={(value) => formatMonth(String(value))}
          formatter={(value, name) => [
            formatNumber(Number(value)),
            name === "cases" ? "Casos" : variableLabel,
          ]}
          contentStyle={{
            borderRadius: 12,
            border: "1px solid var(--color-border)",
            boxShadow: "var(--shadow-card)",
            fontSize: 13,
          }}
        />

        <Area
          yAxisId="cases"
          type="monotone"
          dataKey="cases"
          name="cases"
          stroke="var(--color-primary-600)"
          strokeWidth={2}
          fill="url(#climateCasesFill)"
        />

        <Line
          yAxisId="climate"
          type="monotone"
          dataKey="value"
          name="climate"
          stroke="var(--color-danger)"
          strokeWidth={2}
          dot={false}
          connectNulls
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
