"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { MunicipalityAggregate } from "@/lib/aggregateEpidemiologicalRecords";
import { formatNumber } from "@/lib/utils";

export function MunicipalityCasesChart({ data }: { data: MunicipalityAggregate[] }) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 32)}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
      >
        <CartesianGrid horizontal={false} stroke="var(--color-border)" />

        <XAxis
          type="number"
          tick={{ fontSize: 12, fill: "var(--color-muted)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(value: number) => formatNumber(value)}
        />

        <YAxis
          type="category"
          dataKey="municipality"
          tick={{ fontSize: 12, fill: "var(--color-muted)" }}
          axisLine={false}
          tickLine={false}
          width={140}
        />

        <Tooltip
          formatter={(value) => [formatNumber(Number(value)), "Casos"]}
          contentStyle={{
            borderRadius: 12,
            border: "1px solid var(--color-border)",
            boxShadow: "var(--shadow-card)",
            fontSize: 13,
          }}
        />

        <Bar dataKey="cases" fill="var(--color-primary-500)" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
