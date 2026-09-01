import { PageHeader } from "@/components/ui/PageHeader";
import { StudiesGrid } from "@/components/studies/StudiesGrid";
import { getStudies } from "@/services/studiesService";
import { getMunicipalities } from "@/services/municipalitiesService";

export const dynamic = "force-dynamic";

export default async function StudiesPage() {
  const [studies, municipalities] = await Promise.all([getStudies(), getMunicipalities()]);

  return (
    <div>
      <PageHeader
        title="Estudos"
        description="Cada estudo relaciona uma doença monitorada às variáveis climáticas usadas no modelo de previsão. Clique em um estudo para explorar os dados."
      />

      <StudiesGrid studies={studies} municipalities={municipalities} />
    </div>
  );
}
