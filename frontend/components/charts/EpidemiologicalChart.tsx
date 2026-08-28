"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CaseCurvePoint } from "@/types/epidemiology";
import { formatMonth, formatNumber } from "@/lib/utils";

export function EpidemiologicalChart({ data }: { data: CaseCurvePoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="caseCurveFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-primary-500)" stopOpacity={0.25} />
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
          tick={{ fontSize: 12, fill: "var(--color-muted)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(value: number) => formatNumber(value)}
          width={48}
        />

        <Tooltip
          formatter={(value) => [formatNumber(Number(value)), "Casos"]}
          labelFormatter={(value) => formatMonth(String(value))}
          contentStyle={{
            borderRadius: 12,
            border: "1px solid var(--color-border)",
            boxShadow: "var(--shadow-card)",
            fontSize: 13,
          }}
        />

        <Area
          type="monotone"
          dataKey="cases"
          stroke="var(--color-primary-600)"
          strokeWidth={2}
          fill="url(#caseCurveFill)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
