import { PageHeader } from "@/components/ui/PageHeader";
import { DataExplorer } from "@/components/data/DataExplorer";
import { getMunicipalities } from "@/services/municipalitiesService";

// Municipality list comes from the live Gold table -- must be
// fetched per-request, not baked in at `next build` time.
export const dynamic = "force-dynamic";

export default async function ExploreDataPage() {
  const municipalities = await getMunicipalities();

  return (
    <div>
      <PageHeader
        title="Explorar Dados"
        description="Consulte os dados epidemiológicos e climáticos por doença, município e período."
      />

      <DataExplorer municipalities={municipalities} />
    </div>
  );
}
