import { PageHeader } from "@/components/ui/PageHeader";
import { DataExplorer } from "@/components/data/DataExplorer";

export default function ExploreDataPage() {
  return (
    <div>
      <PageHeader
        title="Explorar Dados"
        description="Consulte os dados epidemiológicos e climáticos por doença, município e período."
      />

      <DataExplorer />
    </div>
  );
}
