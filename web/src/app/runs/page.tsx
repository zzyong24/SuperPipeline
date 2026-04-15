"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { Run } from "@/lib/types";
import { RunStatusBadge } from "@/components/runs/RunStatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    api
      .listRuns()
      .then(setRuns)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered =
    filter === "all" ? runs : runs.filter((r) => r.status === filter);
  const sorted = [...filtered].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">运行记录</h1>
        <Select value={filter} onValueChange={(v) => v && setFilter(v)}>
          <SelectTrigger className="w-36 h-8 text-[13px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="pending">等待中</SelectItem>
            <SelectItem value="running">运行中</SelectItem>
            <SelectItem value="completed">已完成</SelectItem>
            <SelectItem value="failed">失败</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-4 space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : sorted.length === 0 ? (
            <p className="text-sm text-muted-foreground p-6">暂无运行记录</p>
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
                {sorted.map((run) => (
                  <TableRow key={run.run_id} className="cursor-pointer hover:bg-muted/50">
                    <TableCell className="py-2.5">
                      <Link
                        href={`/runs/${run.run_id}`}
                        className="font-mono text-[12px] text-blue-600 hover:underline"
                      >
                        {run.run_id.slice(0, 8)}...
                      </Link>
                    </TableCell>
                    <TableCell className="py-2.5 text-[13px]">
                      {run.pipeline_name}
                    </TableCell>
                    <TableCell className="py-2.5">
                      <RunStatusBadge status={run.status} />
                    </TableCell>
                    <TableCell className="py-2.5 text-[12px] text-muted-foreground">
                      {new Date(run.created_at).toLocaleString("zh-CN", {
                        year: "numeric",
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
