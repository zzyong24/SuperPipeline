"use client";

interface Stage {
  agent: string;
  status: "pending" | "running" | "completed" | "failed";
}

const STATUS_ICONS: Record<string, string> = {
  pending: "⏳",
  running: "🔄",
  completed: "✅",
  failed: "❌",
};

export function PipelineGraph({ stages }: { stages: Stage[] }) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto py-4">
      {stages.map((stage, i) => (
        <div key={stage.agent} className="flex items-center">
          <div className={`px-4 py-3 rounded-lg border-2 text-center min-w-[120px] ${
            stage.status === "running" ? "border-blue-500 bg-blue-50" :
            stage.status === "completed" ? "border-green-500 bg-green-50" :
            stage.status === "failed" ? "border-red-500 bg-red-50" :
            "border-gray-300 bg-gray-50"
          }`}>
            <div className="text-lg">{STATUS_ICONS[stage.status]}</div>
            <div className="text-xs font-medium mt-1">{stage.agent}</div>
          </div>
          {i < stages.length - 1 && <div className="text-gray-300 mx-1">→</div>}
        </div>
      ))}
    </div>
  );
}
