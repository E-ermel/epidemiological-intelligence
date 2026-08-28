/** Mirrors ai/src/epidemiological_agent/api/schemas_data.py's EpidemiologicalRecord. */
export interface EpidemiologicalRecord {
  referenceDate: string;
  disease: string;
  municipality: string;
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
  municipality?: string;
  startDate?: string;
  endDate?: string;
}
