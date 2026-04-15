"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { Run, Content, PipelineState } from "@/lib/types";
import { RunStatusBadge } from "@/components/runs/RunStatusBadge";
import { PipelineProgress } from "@/components/runs/PipelineProgress";
import { ImagePlaceholder } from "@/components/contents/ImagePlaceholder";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Copy, CheckCircle2, XCircle, AlertTriangle, Lightbulb } from "lucide-react";

function getStageStatuses(state?: PipelineState) {
  const statuses: Record<string, "completed" | "running" | "failed" | "pending"> = {
    topic_generator: "pending",
    material_collector: "pending",
    content_generator: "pending",
    reviewer: "pending",
    analyst: "pending",
  };
  if (!state) return statuses;

  const errors = state.errors || [];
  const errAgents = new Set(errors.map((e) => e.agent));

  const checks: [string, boolean][] = [
    ["topic_generator", (state.topics?.length || 0) > 0],
    ["material_collector", (state.materials?.length || 0) > 0],
    ["content_generator", Object.keys(state.contents || {}).length > 0],
    ["reviewer", Object.keys(state.reviews || {}).length > 0],
    ["analyst", !!state.analysis?.summary],
  ];

  let reachedRunning = false;
  for (const [agent, hasData] of checks) {
    if (errAgents.has(agent)) {
      statuses[agent] = "failed";
      reachedRunning = true;
    } else if (hasData) {
      statuses[agent] = "completed";
    } else if (!reachedRunning && state.stage === "running") {
      statuses[agent] = "running";
      reachedRunning = true;
    }
  }
  return statuses;
}

export default function RunDetail() {
  const params = useParams();
  const runId = params.runId as string;
  const [run, setRun] = useState<Run | null>(null);
  const [contents, setContents] = useState<Content[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.getRun(runId), api.listContents({ run_id: runId })])
      .then(([r, c]) => {
        setRun(r);
        setContents(c);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-16" />
        <Skeleton className="h-64" />
      </div>
    );
  }
  if (error) return <p className="text-sm text-red-500">错误: {error}</p>;
  if (!run) return <p className="text-sm text-muted-foreground">未找到运行记录</p>;

  const state = run.state;
  const stageStatuses = getStageStatuses(state);
  const selectedTopic = state?.selected_topic;
  const analysis = state?.analysis;
  const reviews = state?.reviews || {};
  const pContents = state?.contents || {};

  function handleCopy(text: string) {
    navigator.clipboard.writeText(text);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/runs"
          className="inline-flex items-center gap-1 text-[12px] text-muted-foreground hover:text-foreground mb-3"
        >
          <ArrowLeft className="h-3 w-3" /> 返回运行列表
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-lg font-semibold font-mono">{runId.slice(0, 8)}...</h1>
              <RunStatusBadge status={run.status} />
            </div>
            <p className="text-[12px] text-muted-foreground mt-0.5">
              {run.pipeline_name} &middot;{" "}
              {new Date(run.created_at).toLocaleString("zh-CN")}
            </p>
          </div>
        </div>
      </div>

      {/* Pipeline Progress */}
      <Card>
        <CardContent className="py-5 flex justify-center">
          <PipelineProgress stageStatuses={stageStatuses} />
        </CardContent>
      </Card>

      {/* Errors */}
      {state?.errors && state.errors.length > 0 && (
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="py-3 space-y-2">
            {state.errors.map((err, i) => (
              <div key={i} className="flex items-start gap-2 text-[13px]">
                <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                <div>
                  <span className="font-mono font-medium text-red-700">{err.agent}</span>
                  <span className="text-red-600 ml-1">{err.message}</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview" className="text-[13px]">概览</TabsTrigger>
          <TabsTrigger value="content" className="text-[13px]">内容</TabsTrigger>
          <TabsTrigger value="reviews" className="text-[13px]">审核</TabsTrigger>
          <TabsTrigger value="analysis" className="text-[13px]">分析</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4 mt-4">
          {selectedTopic && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">选中选题</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1.5">
                <p className="font-medium text-[14px]">{selectedTopic.title}</p>
                <p className="text-[13px] text-muted-foreground">{selectedTopic.angle}</p>
                <div className="flex gap-4 text-[12px] text-muted-foreground pt-1">
                  <span>评分: <strong>{selectedTopic.score}</strong></span>
                  <span>生成选题数: {state?.topics?.length || 0}</span>
                  <span>素材数: {state?.materials?.length || 0}</span>
                </div>
              </CardContent>
            </Card>
          )}
          {analysis?.summary && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">分析总结</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-[13px] text-muted-foreground leading-relaxed">
                  {analysis.summary}
                </p>
              </CardContent>
            </Card>
          )}
          {!selectedTopic && !analysis?.summary && (
            <p className="text-sm text-muted-foreground">暂无数据，管道运行中...</p>
          )}
        </TabsContent>

        {/* Content Tab */}
        <TabsContent value="content" className="space-y-4 mt-4">
          {Object.keys(pContents).length === 0 && contents.length === 0 ? (
            <p className="text-sm text-muted-foreground">暂未生成内容</p>
          ) : (
            <>
              {Object.entries(pContents).map(([platform, pc]) => (
                <Card key={platform}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        {pc.title}
                        <Badge variant="outline" className="text-[10px]">{platform}</Badge>
                      </CardTitle>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 gap-1 text-[12px]"
                        onClick={() => handleCopy(`${pc.title}\n\n${pc.body}`)}
                      >
                        <Copy className="h-3 w-3" /> 复制
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {pc.image_prompts?.length > 0 && (
                      <div className="grid grid-cols-2 gap-2">
                        {pc.image_prompts.map((prompt, i) => (
                          <ImagePlaceholder key={i} prompt={prompt} />
                        ))}
                      </div>
                    )}
                    <p className="text-[13px] text-muted-foreground whitespace-pre-line leading-relaxed">
                      {pc.body}
                    </p>
                    {pc.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {pc.tags.map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-[10px]">
                            #{tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
              {/* Also show DB contents if available */}
              {contents.length > 0 && Object.keys(pContents).length === 0 && (
                contents.map((c) => (
                  <Card key={c.content_id}>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                          {c.title}
                          <Badge variant="outline" className="text-[10px]">{c.platform}</Badge>
                        </CardTitle>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 gap-1 text-[12px]"
                          onClick={() => handleCopy(`${c.title}\n\n${c.body}`)}
                        >
                          <Copy className="h-3 w-3" /> 复制
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-[13px] text-muted-foreground whitespace-pre-line leading-relaxed">
                        {c.body}
                      </p>
                    </CardContent>
                  </Card>
                ))
              )}
            </>
          )}
        </TabsContent>

        {/* Reviews Tab */}
        <TabsContent value="reviews" className="space-y-3 mt-4">
          {Object.keys(reviews).length === 0 ? (
            <p className="text-sm text-muted-foreground">暂无审核结果</p>
          ) : (
            Object.entries(reviews).map(([platform, review]) => (
              <Card key={platform}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      {platform}
                      {review.passed ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-500" />
                      )}
                    </CardTitle>
                    <Badge
                      variant="outline"
                      className={
                        review.passed
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200 text-[11px]"
                          : "bg-red-50 text-red-700 border-red-200 text-[11px]"
                      }
                    >
                      评分: {review.score}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2">
                  {review.issues?.length > 0 && (
                    <div>
                      <p className="text-[12px] font-medium text-red-600 mb-1">问题</p>
                      <ul className="space-y-0.5">
                        {review.issues.map((issue: string, i: number) => (
                          <li key={i} className="text-[12px] text-red-500 flex items-start gap-1.5">
                            <span className="mt-1.5 w-1 h-1 rounded-full bg-red-400 shrink-0" />
                            {issue}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {review.suggestions?.length > 0 && (
                    <div>
                      <p className="text-[12px] font-medium text-muted-foreground mb-1">建议</p>
                      <ul className="space-y-0.5">
                        {review.suggestions.map((s: string, i: number) => (
                          <li key={i} className="text-[12px] text-muted-foreground flex items-start gap-1.5">
                            <Lightbulb className="h-3 w-3 mt-0.5 shrink-0 text-amber-500" />
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        {/* Analysis Tab */}
        <TabsContent value="analysis" className="space-y-4 mt-4">
          {!analysis?.summary ? (
            <p className="text-sm text-muted-foreground">暂无分析结果</p>
          ) : (
            <>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">总结</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-[13px] text-muted-foreground leading-relaxed">
                    {analysis.summary}
                  </p>
                </CardContent>
              </Card>
              {analysis.insights?.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium">洞察</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-1.5">
                      {analysis.insights.map((insight, i) => (
                        <li key={i} className="text-[13px] text-muted-foreground flex items-start gap-2">
                          <Lightbulb className="h-3.5 w-3.5 mt-0.5 shrink-0 text-amber-500" />
                          {insight}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
              {analysis.improvement_suggestions?.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium">改进建议</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-1.5">
                      {analysis.improvement_suggestions.map((s, i) => (
                        <li key={i} className="text-[13px] text-muted-foreground flex items-start gap-2">
                          <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />
                          {s}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
