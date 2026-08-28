import { PageHeader } from "@/components/ui/PageHeader";
import { StudyCard } from "@/components/studies/StudyCard";
import { getStudies } from "@/services/studiesService";

export const dynamic = "force-dynamic";

export default async function StudiesPage() {
  const studies = await getStudies();

  return (
    <div>
      <PageHeader
        title="Estudos"
        description="Cada estudo relaciona uma doença monitorada às variáveis climáticas usadas no modelo de previsão."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {studies.map((study) => (
          <StudyCard key={study.disease} study={study} />
        ))}
      </div>
    </div>
  );
}
