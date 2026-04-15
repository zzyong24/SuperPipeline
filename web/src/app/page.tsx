"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { Run, Content } from "@/lib/types";
import { StatsCards } from "@/components/dashboard/StatsCards";
import { RunStatusBadge } from "@/components/runs/RunStatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Play, FileText, CheckCircle2, TrendingUp, Plus } from "lucide-react";

export default function Dashboard() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [contents, setContents] = useState<Content[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.listRuns(), api.listContents()])
      .then(([r, c]) => {
        setRuns(r);
        setContents(c);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totalRuns = runs.length;
  const runningCount = runs.filter((r) => r.status === "running").length;
  const totalContents = contents.length;
  const approvedCount = contents.filter(
    (c) => c.status === "approved" || c.status === "published"
  ).length;
  const approvalRate =
    totalContents > 0 ? Math.round((approvedCount / totalContents) * 100) : 0;

  const recentRuns = [...runs]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">仪表盘</h1>
        <Link href="/new">
          <Button size="sm" className="gap-1.5">
            <Plus className="h-4 w-4" />
            新建运行
          </Button>
        </Link>
      </div>

      <StatsCards
        stats={[
          { icon: Play, label: "总运行数", value: totalRuns },
          { icon: TrendingUp, label: "运行中", value: runningCount },
          { icon: FileText, label: "内容数", value: totalContents },
          { icon: CheckCircle2, label: "通过率", value: `${approvalRate}%` },
        ]}
      />

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium">最近运行</CardTitle>
            <Link href="/runs" className="text-[12px] text-muted-foreground hover:text-foreground">
              查看全部 →
            </Link>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {recentRuns.length === 0 ? (
            <p className="text-sm text-muted-foreground px-6 pb-4">
              暂无运行记录，使用 <code className="bg-muted px-1 rounded text-[12px]">sp run</code> 或点击新建运行
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-[12px]">运行 ID</TableHead>
                  <TableHead className="text-[12px]">管道</TableHead>
                  <TableHead className="text-[12px]">状态</TableHead>
                  <TableHead className="text-[12px]">创建时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentRuns.map((run) => (
                  <TableRow key={run.run_id} className="cursor-pointer hover:bg-muted/50">
                    <TableCell className="py-2">
                      <Link
                        href={`/runs/${run.run_id}`}
                        className="font-mono text-[12px] text-blue-600 hover:underline"
                      >
                        {run.run_id.slice(0, 8)}...
                      </Link>
                    </TableCell>
                    <TableCell className="py-2 text-[13px]">{run.pipeline_name}</TableCell>
                    <TableCell className="py-2">
                      <RunStatusBadge status={run.status} />
                    </TableCell>
                    <TableCell className="py-2 text-[12px] text-muted-foreground">
                      {new Date(run.created_at).toLocaleString("zh-CN", {
                        month: "2-digit",
                        day: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
