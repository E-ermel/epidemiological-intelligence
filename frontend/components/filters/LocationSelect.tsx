"use client";

import { useState } from "react";
import type { MunicipalityOption } from "@/types/data";
import { getMunicipalities } from "@/services/municipalitiesService";
import { STATES } from "@/lib/constants";

export interface LocationValue {
  /** Two-letter UF code, or "" for all of Brazil. */
  state: string;
  /** 6-digit municipality code, or "" for the whole state. */
  municipalityCode: string;
}

/**
 * UF -> município pair of selects. A state's municipality list (up to
 * 853, in MG) is fetched when the state is picked, and kept for the
 * rest of the session; municipalities are identified by code, since
 * names repeat across states.
 */
export function LocationSelect({
  value,
  onChange,
  selectClassName,
  labelClassName,
}: {
  value: LocationValue;
  onChange: (value: LocationValue) => void;
  selectClassName: string;
  labelClassName: string;
}) {
  const [byState, setByState] = useState<Record<string, MunicipalityOption[]>>({});
  const [loadingState, setLoadingState] = useState<string | null>(null);

  async function handleStateChange(state: string) {
    onChange({ state, municipalityCode: "" });
    if (!state || byState[state]) return;

    setLoadingState(state);
    try {
      const options = await getMunicipalities(state);
      setByState((current) => ({ ...current, [state]: options }));
    } catch {
      setByState((current) => ({ ...current, [state]: [] }));
    } finally {
      setLoadingState((current) => (current === state ? null : current));
    }
  }

  const municipalities = value.state ? (byState[value.state] ?? []) : [];
  const isLoading = loadingState !== null && loadingState === value.state;

  return (
    <>
      <label className={labelClassName}>
        Estado
        <select
          value={value.state}
          onChange={(e) => handleStateChange(e.target.value)}
          className={selectClassName}
        >
          <option value="">Brasil (todos)</option>
          {STATES.map((s) => (
            <option key={s.code} value={s.code}>
              {s.name}
            </option>
          ))}
        </select>
      </label>

      <label className={labelClassName}>
        Município
        <select
          value={value.municipalityCode}
          onChange={(e) => onChange({ ...value, municipalityCode: e.target.value })}
          disabled={!value.state || isLoading}
          className={selectClassName}
        >
          <option value="">
            {!value.state ? "Escolha um estado" : isLoading ? "Carregando..." : "Todos do estado"}
          </option>
          {municipalities.map((m) => (
            <option key={m.code} value={m.code}>
              {m.name}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}
