"use client";

import { useState } from "react";
import type { StudySummary } from "@/types/study";
import { StudyCard } from "@/components/studies/StudyCard";
import { StudyDashboardModal } from "@/components/studies/StudyDashboardModal";

export function StudiesGrid({
  studies,
  municipalities,
}: {
  studies: StudySummary[];
  municipalities: string[];
}) {
  const [expanded, setExpanded] = useState<{ study: StudySummary; anchor: DOMRect } | null>(null);

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {studies.map((study) => (
          <StudyCard
            key={study.disease}
            study={study}
            onExpand={(anchor) => setExpanded({ study, anchor })}
          />
        ))}
      </div>

      {expanded && (
        <StudyDashboardModal
          study={expanded.study}
          anchorRect={expanded.anchor}
          municipalities={municipalities}
          onClose={() => setExpanded(null)}
        />
      )}
    </>
  );
}
