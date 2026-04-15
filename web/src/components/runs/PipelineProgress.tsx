import { cn } from "@/lib/utils";
import { Check, Loader2, X } from "lucide-react";

const STAGES = [
  { key: "topic_generator", label: "选题" },
  { key: "material_collector", label: "素材" },
  { key: "content_generator", label: "内容" },
  { key: "reviewer", label: "审核" },
  { key: "analyst", label: "分析" },
];

interface PipelineProgressProps {
  stageStatuses: Record<string, "completed" | "running" | "failed" | "pending">;
}

export function PipelineProgress({ stageStatuses }: PipelineProgressProps) {
  return (
    <div className="flex items-center gap-0">
      {STAGES.map((stage, i) => {
        const status = stageStatuses[stage.key] || "pending";
        return (
          <div key={stage.key} className="flex items-center">
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium border-2 transition-colors",
                  status === "completed" && "bg-emerald-50 border-emerald-400 text-emerald-600",
                  status === "running" && "bg-blue-50 border-blue-400 text-blue-600 animate-pulse",
                  status === "failed" && "bg-red-50 border-red-400 text-red-600",
                  status === "pending" && "bg-muted border-border text-muted-foreground"
                )}
              >
                {status === "completed" && <Check className="h-4 w-4" />}
                {status === "running" && <Loader2 className="h-4 w-4 animate-spin" />}
                {status === "failed" && <X className="h-4 w-4" />}
                {status === "pending" && <span>{i + 1}</span>}
              </div>
              <span
                className={cn(
                  "text-[11px] font-medium",
                  status === "completed" && "text-emerald-600",
                  status === "running" && "text-blue-600",
                  status === "failed" && "text-red-600",
                  status === "pending" && "text-muted-foreground"
                )}
              >
                {stage.label}
              </span>
            </div>
            {i < STAGES.length - 1 && (
              <div
                className={cn(
                  "w-12 h-0.5 mx-1 mt-[-18px]",
                  status === "completed" ? "bg-emerald-300" : "bg-border"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
