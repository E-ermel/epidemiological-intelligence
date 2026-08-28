"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { DiseaseDistributionSlice } from "@/types/epidemiology";
import { formatNumber } from "@/lib/utils";

const COLORS = [
  "var(--color-primary-600)",
  "var(--color-primary-500)",
  "#60a5fa",
  "#93c5fd",
  "#bfdbfe",
  "#dbeafe",
];

export function DiseaseDistributionChart({ data }: { data: DiseaseDistributionSlice[] }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={data}
          dataKey="cases"
          nameKey="label"
          innerRadius={52}
          outerRadius={80}
          paddingAngle={2}
          strokeWidth={0}
        >
          {data.map((entry, index) => (
            <Cell key={entry.disease} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => [formatNumber(Number(value)), "Casos"]}
          contentStyle={{
            borderRadius: 12,
            border: "1px solid var(--color-border)",
            boxShadow: "var(--shadow-card)",
            fontSize: 13,
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
