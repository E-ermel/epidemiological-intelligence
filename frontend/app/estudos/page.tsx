import { PageHeader } from "@/components/ui/PageHeader";
import { StudiesGrid } from "@/components/studies/StudiesGrid";
import { getStudies } from "@/services/studiesService";

export const dynamic = "force-dynamic";

export default async function StudiesPage() {
  const studies = await getStudies();

  return (
    <div>
      <PageHeader
        title="Estudos"
        description="Cada estudo acompanha uma doença ou agravo monitorado e sua relação com o clima. Clique em um estudo para explorar os dados."
      />

      <StudiesGrid studies={studies} />
    </div>
  );
}
