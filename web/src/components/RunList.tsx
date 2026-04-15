"use client";

import Link from "next/link";

interface Run {
  run_id: string;
  pipeline_name: string;
  status: string;
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-100 text-green-800",
  running: "bg-blue-100 text-blue-800",
  failed: "bg-red-100 text-red-800",
  pending: "bg-gray-100 text-gray-800",
};

export function RunList({ runs }: { runs: Run[] }) {
  return (
    <div className="space-y-2">
      {runs.map((run) => (
        <Link key={run.run_id} href={`/runs/${run.run_id}`} className="block p-4 border rounded-lg hover:bg-gray-50">
          <div className="flex justify-between items-center">
            <div>
              <span className="font-mono text-sm text-gray-500">{run.run_id}</span>
              <span className="ml-2 font-medium">{run.pipeline_name}</span>
            </div>
            <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[run.status] || ""}`}>
              {run.status}
            </span>
          </div>
          <div className="text-xs text-gray-400 mt-1">{run.created_at}</div>
        </Link>
      ))}
    </div>
  );
}
