import { PipelineGraph } from "@/components/PipelineGraph";

export default async function RunDetail({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const stages = [
    { agent: "topic_generator", status: "completed" as const },
    { agent: "material_collector", status: "completed" as const },
    { agent: "content_generator", status: "running" as const },
    { agent: "reviewer", status: "pending" as const },
    { agent: "analyst", status: "pending" as const },
  ];

  return (
    <main className="max-w-4xl mx-auto p-6">
      <h1 className="text-xl font-bold mb-4">Run: {runId}</h1>
      <PipelineGraph stages={stages} />
    </main>
  );
}
