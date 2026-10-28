import type { EpidemiologicalRecord } from "@/types/data";
import type { GeoArea } from "@/types/map";

export interface MonthlyAggregate {
  referenceDate: string;
  cases: number;
  value: number | null;
}

/**
 * Collapses raw per-municipality-per-month records (as returned by
 * GET /data) into one point per month -- summing cases, averaging the
 * chosen climate variable across whichever municipalities are in the
 * result set. A no-op reshape when the caller already filtered to a
 * single municipality (one record per month already).
 */
export function aggregateByMonth(
  records: EpidemiologicalRecord[],
  climateField: keyof EpidemiologicalRecord
): MonthlyAggregate[] {
  const byDate = new Map<string, { cases: number; sum: number; count: number }>();

  for (const record of records) {
    const entry = byDate.get(record.referenceDate) ?? { cases: 0, sum: 0, count: 0 };
    entry.cases += record.cases ?? 0;

    const value = record[climateField];
    if (typeof value === "number") {
      entry.sum += value;
      entry.count += 1;
    }

    byDate.set(record.referenceDate, entry);
  }

  return [...byDate.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([referenceDate, entry]) => ({
      referenceDate,
      cases: entry.cases,
      value: entry.count > 0 ? entry.sum / entry.count : null,
    }));
}

export interface SeasonalAggregate {
  month: number;
  avgCases: number;
}

/**
 * Average total monthly cases per calendar month (Jan..Dez), across
 * every year in the filtered set -- summed across municipalities
 * first (one real total per year-month) so a broader municipality
 * filter doesn't inflate the average with duplicate per-municipality
 * rows, then averaged across however many years of that month are
 * present. Surfaces the seasonal pattern each disease's description
 * already references (e.g. leptospirose's rain-season peak).
 */
export function aggregateSeasonality(records: EpidemiologicalRecord[]): SeasonalAggregate[] {
  const totalsByExactMonth = new Map<string, number>();

  for (const record of records) {
    totalsByExactMonth.set(
      record.referenceDate,
      (totalsByExactMonth.get(record.referenceDate) ?? 0) + (record.cases ?? 0)
    );
  }

  const byCalendarMonth = new Map<number, { sum: number; count: number }>();

  for (const [referenceDate, total] of totalsByExactMonth) {
    const month = new Date(referenceDate).getUTCMonth() + 1;
    const entry = byCalendarMonth.get(month) ?? { sum: 0, count: 0 };
    entry.sum += total;
    entry.count += 1;
    byCalendarMonth.set(month, entry);
  }

  return Array.from({ length: 12 }, (_, i) => {
    const month = i + 1;
    const entry = byCalendarMonth.get(month);
    return { month, avgCases: entry ? entry.sum / entry.count : 0 };
  });
}

export interface MunicipalityAggregate {
  /** Bar label: a state name or a municipality name. */
  municipality: string;
  cases: number;
}

/**
 * The `limit` areas with most cases, from GET /geo/{level} -- states
 * for all of Brazil, municipalities within a state. GET /data comes
 * aggregated per month when no municipality is chosen, so it no longer
 * carries a per-municipality breakdown to rank.
 */
export function topAreas(areas: GeoArea[], limit = 8): MunicipalityAggregate[] {
  return areas
    .filter((area) => area.cases > 0)
    .map((area) => ({ municipality: area.name, cases: area.cases }))
    .sort((a, b) => b.cases - a.cases)
    .slice(0, limit);
}
