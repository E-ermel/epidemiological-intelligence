/** Mirrors ai/src/epidemiological_agent/api/schemas_data.py's EpidemiologicalRecord. */
export interface EpidemiologicalRecord {
  referenceDate: string;
  disease: string;
  /** Municipality name, or the state/"BRASIL" label for aggregated records. */
  municipality: string;
  state: string | null;
  /** null when the record is aggregated over a state or Brazil. */
  municipalityCode: string | null;
  cases: number | null;
  precipitationSumMm: number | null;
  precipitationMaxObservationMm: number | null;
  temperatureAvgC: number | null;
  dewPointAvgC: number | null;
  relativeHumidityAvgPct: number | null;
  atmosphericPressureAvgMb: number | null;
  windSpeedAvgMs: number | null;
  windGustMaxMs: number | null;
}

export interface EpidemiologicalDataFilters {
  disease?: string;
  /** Two-letter UF code. */
  state?: string;
  /** 6-digit DATASUS code -- names alone repeat across states. */
  municipalityCode?: string;
  startDate?: string;
  endDate?: string;
}

/** Mirrors ai/src/epidemiological_agent/api/schemas_geo.py's MunicipalityOption. */
export interface MunicipalityOption {
  code: string;
  name: string;
  state: string;
}
