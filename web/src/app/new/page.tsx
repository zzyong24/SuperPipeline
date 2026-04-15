"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api-client";
import type { Pipeline, PipelineDetail, StageConfig } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Loader2, Workflow, ChevronDown, ChevronRight, Settings2 } from "lucide-react";
import { cn } from "@/lib/utils";

const AGENT_NAMES: Record<string, string> = {
  topic_generator: "选题生成",
  material_collector: "素材采集",
  content_generator: "内容生成",
  reviewer: "内容审核",
  analyst: "复盘分析",
};

const CONFIG_LABELS: Record<string, string> = {
  style: "风格",
  count: "生成数量",
  sources: "素材来源",
  max_items: "最大素材数",
  platform: "目标平台",
  format: "内容格式",
  rules: "审核规则",
  min_score: "最低评分",
  metrics: "分析指标",
  temperature: "创意度",
};

export default function NewRunPage() {
  return (
    <Suspense fallback={<div className="text-sm text-muted-foreground">加载中...</div>}>
      <NewRunContent />
    </Suspense>
  );
}

function NewRunContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselect = searchParams.get("pipeline") || "";
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPipeline, setSelectedPipeline] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<string>("");
  const [pipelineDetail, setPipelineDetail] = useState<PipelineDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [brief, setBrief] = useState("");
  const [keywords, setKeywords] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [stageOverrides, setStageOverrides] = useState<Record<string, Record<string, any>>>({});
  const [expandedStages, setExpandedStages] = useState<Set<string>>(new Set());

  useEffect(() => {
    api
      .listPipelines()
      .then((p) => {
        setPipelines(p);
        // Check URL param for preselection
        const match = preselect ? p.find((x) => x.file === preselect) : null;
        if (match) {
          setSelectedPipeline(match.name);
          setSelectedFile(match.file);
        } else if (p.length > 0) {
          setSelectedPipeline(p[0].name);
          setSelectedFile(p[0].file);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Fetch pipeline detail when selection changes
  useEffect(() => {
    if (!selectedFile) return;
    setDetailLoading(true);
    setPipelineDetail(null);
    setStageOverrides({});
    setExpandedStages(new Set());
    // file field includes .yaml extension, strip it
    const fileName = selectedFile.replace(/\.yaml$/, "");
    api
      .getPipeline(fileName)
      .then(setPipelineDetail)
      .catch(() => setPipelineDetail(null))
      .finally(() => setDetailLoading(false));
  }, [selectedFile]);

  function handleSelectPipeline(p: Pipeline) {
    setSelectedPipeline(p.name);
    setSelectedFile(p.file);
  }

  function toggleStage(agent: string) {
    setExpandedStages((prev) => {
      const next = new Set(prev);
      if (next.has(agent)) next.delete(agent);
      else next.add(agent);
      return next;
    });
  }

  function handleConfigChange(agent: string, key: string, value: string) {
    setStageOverrides((prev) => ({
      ...prev,
      [agent]: {
        ...(prev[agent] || {}),
        [key]: value,
      },
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedPipeline || !brief.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      const kw = keywords
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      // Only include non-empty overrides
      const overrides: Record<string, Record<string, any>> = {};
      for (const [agent, configs] of Object.entries(stageOverrides)) {
        const nonEmpty: Record<string, any> = {};
        for (const [k, v] of Object.entries(configs)) {
          if (v !== "" && v !== undefined) nonEmpty[k] = v;
        }
        if (Object.keys(nonEmpty).length > 0) overrides[agent] = nonEmpty;
      }
      const result = await api.createRun({
        pipeline: selectedFile.replace(/\.yaml$/, ""),
        brief: brief.trim(),
        keywords: kw.length > 0 ? kw : undefined,
        stage_overrides: Object.keys(overrides).length > 0 ? overrides : undefined,
      });
      router.push(`/runs/${result.run_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "创建运行失败");
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4 max-w-2xl">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-lg font-semibold">新建运行</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Pipeline selector */}
        <div className="space-y-2">
          <label className="text-[13px] font-medium">选择管道</label>
          <div className="grid grid-cols-1 gap-2">
            {pipelines.map((p) => (
              <Card
                key={p.name}
                className={cn(
                  "cursor-pointer transition-colors",
                  selectedPipeline === p.name
                    ? "border-primary ring-1 ring-primary"
                    : "hover:border-muted-foreground/30"
                )}
                onClick={() => handleSelectPipeline(p)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="h-8 w-8 rounded-md bg-muted flex items-center justify-center mt-0.5">
                      <Workflow className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-[13px]">{p.name}</p>
                      <p className="text-[12px] text-muted-foreground mt-0.5">
                        {p.description}
                      </p>
                      <div className="flex gap-1.5 mt-2">
                        {p.platforms.map((platform) => (
                          <Badge key={platform} variant="secondary" className="text-[10px]">
                            {platform}
                          </Badge>
                        ))}
                        <Badge variant="outline" className="text-[10px]">
                          {p.stages} 个节点
                        </Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          {pipelines.length === 0 && (
            <p className="text-[12px] text-muted-foreground">
              未找到管道配置，请检查后端服务
            </p>
          )}
        </div>

        {/* Stage config */}
        {selectedPipeline && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-muted-foreground" />
              <label className="text-[13px] font-medium">节点配置</label>
            </div>
            {detailLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-10" />
                ))}
              </div>
            ) : pipelineDetail?.stages ? (
              <div className="border rounded-lg divide-y">
                {pipelineDetail.stages.map((stage, idx) => {
                  const agentName = AGENT_NAMES[stage.agent] || stage.agent;
                  const isExpanded = expandedStages.has(stage.agent);
                  const configEntries = Object.entries(stage.config || {});

                  return (
                    <div key={stage.agent}>
                      <button
                        type="button"
                        className="w-full flex items-center gap-2 px-3 py-2.5 text-[13px] hover:bg-muted/50 transition-colors"
                        onClick={() => toggleStage(stage.agent)}
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                        )}
                        <span className="font-medium">{agentName}</span>
                        <span className="text-[11px] text-muted-foreground ml-auto">
                          {configEntries.length} 项配置
                        </span>
                      </button>
                      {isExpanded && configEntries.length > 0 && (
                        <div className="px-3 pb-3 pt-1 space-y-2 bg-muted/20">
                          {configEntries.map(([key, defaultValue]) => {
                            const label = CONFIG_LABELS[key] || key;
                            const overrideValue = stageOverrides[stage.agent]?.[key];
                            const displayValue = overrideValue !== undefined ? overrideValue : "";
                            return (
                              <div key={key} className="flex items-center gap-3">
                                <label className="text-[12px] text-muted-foreground w-24 shrink-0">
                                  {label}
                                </label>
                                <Input
                                  className="h-7 text-[12px] flex-1"
                                  placeholder={String(defaultValue)}
                                  value={displayValue}
                                  onChange={(e) =>
                                    handleConfigChange(stage.agent, key, e.target.value)
                                  }
                                />
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-[12px] text-muted-foreground">
                无法加载节点配置
              </p>
            )}
          </div>
        )}

        <Separator />

        {/* Brief */}
        <div className="space-y-2">
          <label htmlFor="brief" className="text-[13px] font-medium">
            主题 / 简报
          </label>
          <Textarea
            id="brief"
            placeholder="描述你想要生成的内容主题..."
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            rows={4}
            className="text-[13px]"
          />
        </div>

        {/* Keywords */}
        <div className="space-y-2">
          <label htmlFor="keywords" className="text-[13px] font-medium">
            关键词 <span className="text-muted-foreground">（可选，逗号分隔）</span>
          </label>
          <Input
            id="keywords"
            placeholder="关键词1, 关键词2, ..."
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            className="text-[13px]"
          />
        </div>

        {error && (
          <p className="text-[13px] text-red-500">{error}</p>
        )}

        <Button
          type="submit"
          disabled={!selectedPipeline || !brief.trim() || submitting}
          className="w-full"
        >
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              创建中...
            </>
          ) : (
            "开始运行"
          )}
        </Button>
      </form>
    </div>
  );
}
