import { RunList } from "@/components/RunList";

export default function Dashboard() {
  return (
    <main className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">SuperPipeline</h1>
      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-3">Recent Runs</h2>
        <RunList runs={[]} />
        <p className="text-sm text-gray-400 mt-2">Connect API to see runs</p>
      </section>
    </main>
  );
}
