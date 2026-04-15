import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const statusConfig: Record<string, { label: string; className: string }> = {
  completed: {
    label: "已完成",
    className: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  running: {
    label: "运行中",
    className: "bg-blue-50 text-blue-700 border-blue-200 animate-pulse",
  },
  failed: {
    label: "失败",
    className: "bg-red-50 text-red-700 border-red-200",
  },
  pending: {
    label: "等待中",
    className: "bg-muted text-muted-foreground border-border",
  },
};

export function RunStatusBadge({ status }: { status: string }) {
  const config = statusConfig[status] || statusConfig.pending;
  return (
    <Badge
      variant="outline"
      className={cn("text-[11px] font-medium", config.className)}
    >
      {config.label}
    </Badge>
  );
}
