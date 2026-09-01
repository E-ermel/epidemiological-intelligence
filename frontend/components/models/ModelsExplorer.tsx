"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { DiseaseCode } from "@/types/epidemiology";
import type { ModelMetadata, ObservedVsPredictedPoint } from "@/types/model";
import { ModelCard } from "@/components/models/ModelCard";
import { ModelDetail } from "@/components/models/ModelDetail";
import { UntrainedModelPanel } from "@/components/models/UntrainedModelPanel";
import { AllModelsPanel } from "@/components/models/AllModelsPanel";
import type { RetrainStatus } from "@/components/models/RetrainButton";
import { DISEASES } from "@/lib/constants";
import {
  getRetrainStatus,
  retrainAllModels,
  retrainDiseaseModel,
} from "@/services/modelsService";

interface ModelsExplorerProps {
  models: ModelMetadata[];
  observedVsPredictedByDisease: Record<string, ObservedVsPredictedPoint[]>;
}

/** Key used in retrainState for the bulk "Retreinar modelos" action --
 * distinct from any DiseaseCode so it can't collide with a per-disease
 * entry. */
const ALL_MODELS_KEY = "__all__";
type RetrainKey = DiseaseCode | typeof ALL_MODELS_KEY;

interface RetrainEntry {
  status: RetrainStatus;
  executionName?: string;
}

/** How often to re-check an in-progress execution. The job itself can
 * take up to an hour, so there's no need to poll aggressively. */
const POLL_INTERVAL_MS = 5000;

/** Persisted so the retrain button stays locked across navigation/reload
 * while a Cloud Run Job execution is still running -- otherwise leaving
 * `/modelos` and coming back unmounts this component, dropping the
 * in-memory retrainState and making an in-progress job look "idle"
 * again. */
const RETRAIN_STATE_STORAGE_KEY = "epi-intel:retrain-state";

function loadStoredRetrainState(): Partial<Record<RetrainKey, RetrainEntry>> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(RETRAIN_STATE_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Partial<Record<RetrainKey, RetrainEntry>>;
    // Drop entries stuck mid-request ("loading" with no executionName yet)
    // -- there's nothing to resume polling for, so treat them as idle
    // rather than leaving the button permanently disabled.
    const sanitized: Partial<Record<RetrainKey, RetrainEntry>> = {};
    for (const [key, entry] of Object.entries(parsed)) {
      if (entry && (entry.executionName || entry.status !== "loading")) {
        sanitized[key as RetrainKey] = entry;
      }
    }
    return sanitized;
  } catch {
    return {};
  }
}

/**
 * Lists every monitored disease (not just the ones with a trained
 * model) so a disease without a model still shows up -- as a
 * "sem modelo" card with a way to trigger training -- instead of
 * silently falling back to whichever model happens to be first.
 * No disease selected by default: clicking a card selects it, and
 * clicking the selected card again deselects it, back to the panel
 * with the bulk "Retreinar modelos" action.
 *
 * A retrain button stays disabled from the moment it's clicked until
 * the triggered Cloud Run Job execution actually finishes -- not just
 * until it's accepted -- by polling GET /models/retrain/status for the
 * returned executionName every POLL_INTERVAL_MS.
 */
export function ModelsExplorer({ models, observedVsPredictedByDisease }: ModelsExplorerProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedDisease = searchParams.get("disease") as DiseaseCode | null;

  const modelByDisease = useMemo(
    () => new Map(models.map((model) => [model.disease, model])),
    [models]
  );

  const [selected, setSelected] = useState<DiseaseCode | null>(
    requestedDisease && DISEASES.some((d) => d.code === requestedDisease)
      ? requestedDisease
      : null
  );

  const [retrainState, setRetrainState] = useState<Partial<Record<RetrainKey, RetrainEntry>>>(
    loadStoredRetrainState
  );

  useEffect(() => {
    try {
      window.localStorage.setItem(RETRAIN_STATE_STORAGE_KEY, JSON.stringify(retrainState));
    } catch {
      // Storage unavailable (private mode, quota, etc.) -- retrain still
      // works within the session, it just won't survive navigation.
    }
  }, [retrainState]);

  async function startRetrain(key: RetrainKey, trigger: () => Promise<string>) {
    setRetrainState((prev) => ({ ...prev, [key]: { status: "loading" } }));
    try {
      const executionName = await trigger();
      setRetrainState((prev) => ({ ...prev, [key]: { status: "running", executionName } }));
    } catch {
      setRetrainState((prev) => ({ ...prev, [key]: { status: "error" } }));
    }
  }

  // Self-scheduling poll: re-runs whenever retrainState changes, and
  // stops on its own once nothing is "running" anymore (no next
  // setTimeout gets scheduled).
  useEffect(() => {
    const running = Object.entries(retrainState).filter(
      ([, entry]) => entry?.status === "running" && entry.executionName
    ) as [RetrainKey, RetrainEntry][];

    if (running.length === 0) return;

    const timer = setTimeout(async () => {
      for (const [key, entry] of running) {
        if (!entry.executionName) continue;
        try {
          const result = await getRetrainStatus(entry.executionName);
          setRetrainState((prev) => ({
            ...prev,
            [key]: { ...prev[key], status: result.status },
          }));
          if (result.status === "succeeded") {
            // Model list/metrics are server-fetched props -- refresh
            // to pick up the newly trained version without a reload.
            router.refresh();
          }
        } catch {
          setRetrainState((prev) => ({ ...prev, [key]: { ...prev[key], status: "error" } }));
        }
      }
    }, POLL_INTERVAL_MS);

    return () => clearTimeout(timer);
  }, [retrainState, router]);

  const selectedModel = selected ? modelByDisease.get(selected) : undefined;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <div className="flex flex-col gap-3">
        {DISEASES.map(({ code, label }) => (
          <ModelCard
            key={code}
            model={modelByDisease.get(code)}
            label={label}
            isSelected={code === selected}
            onSelect={() => setSelected((prev) => (prev === code ? null : code))}
          />
        ))}
      </div>

      <div className="lg:col-span-2">
        {selected == null ? (
          <AllModelsPanel
            retrainStatus={retrainState[ALL_MODELS_KEY]?.status ?? "idle"}
            onRetrainAll={() => startRetrain(ALL_MODELS_KEY, retrainAllModels)}
          />
        ) : selectedModel ? (
          <ModelDetail
            label={DISEASES.find((d) => d.code === selected)?.label ?? selected}
            model={selectedModel}
            observedVsPredicted={observedVsPredictedByDisease[selectedModel.disease] ?? []}
            retrainStatus={retrainState[selected]?.status ?? "idle"}
            onRetrain={() => startRetrain(selected, () => retrainDiseaseModel(selected))}
          />
        ) : (
          <UntrainedModelPanel
            label={DISEASES.find((d) => d.code === selected)?.label ?? selected}
            retrainStatus={retrainState[selected]?.status ?? "idle"}
            onRetrain={() => startRetrain(selected, () => retrainDiseaseModel(selected))}
          />
        )}
      </div>
    </div>
  );
}
