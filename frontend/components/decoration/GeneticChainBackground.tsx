"use client";

import { useEffect, useState } from "react";
import type { DiseaseDistributionSlice } from "@/types/epidemiology";
import { getOverviewData } from "@/services/overviewService";
import { DISEASE_COLORS } from "@/lib/constants";

/**
 * Full-page decorative background: one "chain" per disease -- a
 * sequence of connected nodes along a gentle wave, evoking a DNA
 * strand -- sized by that disease's real case count and colored by
 * DISEASE_COLORS. "Reactive" here means data-driven, not real-time:
 * it fetches once (see below) and the chain lengths reflect that
 * snapshot, with a one-time draw-in animation, not a continuous
 * pulse -- see the Fase 3 plan for why.
 *
 * Fetches its own data client-side on mount rather than being fed
 * from the server layout, specifically so app/layout.tsx (which wraps
 * every route) doesn't need `force-dynamic` just for this decoration.
 * Layouts persist across client-side navigations in the App Router,
 * so this only fetches once per session, not per page. Silently
 * renders nothing on error or before data arrives -- a decoration
 * must never surface an error state or block the real page.
 */

const VIEWBOX_SIZE = 1000;
const MIN_NODES = 6;
const MAX_EXTRA_NODES = 18;

function hashString(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i++) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0;
  }
  return hash;
}

interface ChainPoint {
  x: number;
  y: number;
}

interface ChainSpec {
  disease: string;
  color: string;
  points: ChainPoint[];
}

function buildChainSpecs(distribution: DiseaseDistributionSlice[]): ChainSpec[] {
  const maxCases = Math.max(1, ...distribution.map((d) => d.cases));

  return distribution.map((slice, index) => {
    const hash = hashString(slice.disease);

    const laneY = 100 + (index / Math.max(1, distribution.length - 1)) * 800 + ((hash % 60) - 30);
    const amplitude = 30 + (hash % 50);
    const phase = (hash % 628) / 100;
    const frequency = 0.5 + ((hash >> 8) % 30) / 100;

    const nodeCount = Math.round(
      MIN_NODES + (slice.cases / maxCases) * MAX_EXTRA_NODES
    );

    const points: ChainPoint[] = Array.from({ length: nodeCount }, (_, i) => {
      const x = (i / Math.max(1, nodeCount - 1)) * VIEWBOX_SIZE;
      const y = laneY + amplitude * Math.sin(phase + i * frequency);
      return { x, y };
    });

    return {
      disease: slice.disease,
      color: DISEASE_COLORS[slice.disease as keyof typeof DISEASE_COLORS] ?? "var(--color-primary-500)",
      points,
    };
  });
}

export function GeneticChainBackground() {
  const [distribution, setDistribution] = useState<DiseaseDistributionSlice[] | null>(null);

  useEffect(() => {
    let cancelled = false;

    getOverviewData()
      .then((data) => {
        if (!cancelled) setDistribution(data.diseaseDistribution);
      })
      .catch(() => {
        // Decorative only -- never surface an error for this.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (!distribution || distribution.length === 0) return null;

  const chains = buildChainSpecs(distribution);

  return (
    <svg
      className="pointer-events-none fixed inset-0 h-full w-full"
      viewBox={`0 0 ${VIEWBOX_SIZE} ${VIEWBOX_SIZE}`}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {chains.map((chain) => (
        <g key={chain.disease} opacity={0.07}>
          <polyline
            points={chain.points.map((p) => `${p.x},${p.y}`).join(" ")}
            fill="none"
            stroke={chain.color}
            strokeWidth={2}
            pathLength={100}
            strokeDasharray={100}
            strokeDashoffset={0}
            className="chain-line"
          />
          {chain.points.map((p, i) => (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r={i % 2 === 0 ? 6 : 3.5}
              fill={chain.color}
              opacity={1}
              className="chain-node"
              style={{ animationDelay: `${i * 70}ms` }}
            />
          ))}
        </g>
      ))}
    </svg>
  );
}
