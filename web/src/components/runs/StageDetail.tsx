"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { StageSnapshot } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { Loader2, Play, Save, X, Clock, History } from "lucide-react";

const AGENT_NAMES: Record<string, string> = {
  topic_generator: "选题生成",
  material_collector: "素材采集",
  content_generator: "内容生成",
  reviewer: "内容审核",
  analyst: "复盘分析",
};

const STATUS_STYLES: Record<string, string> = {
  completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  running: "bg-blue-50 text-blue-700 border-blue-200",
  failed: "bg-red-50 text-red-700 border-red-200",
  pending: "bg-muted text-muted-foreground border-border",
};

const STATUS_LABELS: Record<string, string> = {
  completed: "已完成",
  running: "运行中",
  failed: "失败",
  pending: "待运行",
};

interface StageDetailProps {
  runId: string;
  agent: string;
  onClose: () => void;
  onRerun?: () => void;
}

export function StageDetail({ runId, agent, onClose, onRerun }: StageDetailProps) {
  const [snapshot, setSnapshot] = useState<StageSnapshot | null>(null);
  const [history, setHistory] = useState<StageSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editJson, setEditJson] = useState("");
  const [saving, setSaving] = useState(false);
  const [rerunning, setRerunning] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    api
      .getStage(runId, agent)
      .then((s) => {
        setSnapshot(s);
        setEditJson(JSON.stringify(s.outputs ?? {}, null, 2));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [runId, agent]);

  function loadHistory() {
    api
      .getStageHistory(runId, agent)
      .then(setHistory)
      .catch(() => {});
  }

  function loadVersion(version: number) {
    setLoading(true);
    api
      .getStage(runId, agent, version)
      .then((s) => {
        setSnapshot(s);
        setEditJson(JSON.stringify(s.outputs ?? {}, null, 2));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  async function handleSave() {
    setSaving(true);
    setSaveMsg("");
    try {
      const outputs = JSON.parse(editJson);
      const updated = await api.editStageOutputs(runId, agent, outputs);
      setSnapshot(updated);
      setSaveMsg("已保存");
      setTimeout(() => setSaveMsg(""), 2000);
    } catch (e: any) {
      setSaveMsg(e.message || "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleRerun() {
    setRerunning(true);
    try {
      await api.rerunStage(runId, agent, {});
      onRerun?.();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRerunning(false);
    }
  }

  const agentLabel = AGENT_NAMES[agent] || agent;

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8 flex items-center justify-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          加载节点详情...
        </CardContent>
      </Card>
    );
  }

  if (error && !snapshot) {
    return (
      <Card>
        <CardContent className="py-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-red-500">加载失败: {error}</p>
            <Button size="sm" variant="ghost" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!snapshot) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <CardTitle className="text-sm font-semibold">{agentLabel}</CardTitle>
            <Badge variant="outline" className={`text-[10px] ${STATUS_STYLES[snapshot.status] || ""}`}>
              {STATUS_LABELS[snapshot.status] || snapshot.status}
            </Badge>
            <span className="text-[11px] text-muted-foreground font-mono">v{snapshot.version}</span>
            {snapshot.duration_ms != null && (
              <span className="text-[11px] text-muted-foreground flex items-center gap-0.5">
                <Clock className="h-3 w-3" />
                {(snapshot.duration_ms / 1000).toFixed(1)}s
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <Button
              size="sm"
              variant="outline"
              className="h-7 gap-1 text-[12px]"
              onClick={handleRerun}
              disabled={rerunning}
            >
              {rerunning ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
              重跑
            </Button>
            <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
        {snapshot.error && (
          <p className="text-[12px] text-red-500 mt-1.5">{snapshot.error}</p>
        )}
      </CardHeader>
      <Separator />
      <CardContent className="pt-3">
        <Tabs defaultValue="outputs">
          <TabsList className="h-8">
            <TabsTrigger value="outputs" className="text-[12px] h-6">输出</TabsTrigger>
            <TabsTrigger value="inputs" className="text-[12px] h-6">输入</TabsTrigger>
            <TabsTrigger value="config" className="text-[12px] h-6">配置</TabsTrigger>
            <TabsTrigger
              value="history"
              className="text-[12px] h-6"
              onClick={loadHistory}
            >
              历史
            </TabsTrigger>
          </TabsList>

          <TabsContent value="outputs" className="mt-3 space-y-2">
            <Textarea
              className="font-mono text-[12px] min-h-[200px] resize-y"
              value={editJson}
              onChange={(e) => setEditJson(e.target.value)}
            />
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                className="h-7 gap-1 text-[12px]"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
                保存修改
              </Button>
              {saveMsg && (
                <span className={`text-[12px] ${saveMsg === "已保存" ? "text-emerald-600" : "text-red-500"}`}>
                  {saveMsg}
                </span>
              )}
            </div>
          </TabsContent>

          <TabsContent value="inputs" className="mt-3">
            <pre className="text-[12px] font-mono bg-muted rounded-md p-3 overflow-auto max-h-[300px] whitespace-pre-wrap">
              {JSON.stringify(snapshot.inputs, null, 2)}
            </pre>
          </TabsContent>

          <TabsContent value="config" className="mt-3">
            <pre className="text-[12px] font-mono bg-muted rounded-md p-3 overflow-auto max-h-[300px] whitespace-pre-wrap">
              {JSON.stringify(snapshot.config, null, 2)}
            </pre>
          </TabsContent>

          <TabsContent value="history" className="mt-3">
            {history.length === 0 ? (
              <p className="text-[12px] text-muted-foreground">暂无历史版本</p>
            ) : (
              <div className="space-y-1.5">
                {history.map((h) => (
                  <button
                    key={h.id}
                    onClick={() => loadVersion(h.version)}
                    className={`w-full text-left px-3 py-2 rounded-md border text-[12px] hover:bg-muted/50 transition-colors ${
                      h.version === snapshot.version ? "border-primary bg-muted/50" : "border-border"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <History className="h-3 w-3 text-muted-foreground" />
                        <span className="font-mono font-medium">v{h.version}</span>
                        <Badge variant="outline" className={`text-[9px] ${STATUS_STYLES[h.status] || ""}`}>
                          {STATUS_LABELS[h.status] || h.status}
                        </Badge>
                      </span>
                      <span className="text-muted-foreground">
                        {new Date(h.created_at).toLocaleString("zh-CN")}
                      </span>
                    </div>
                    {h.duration_ms != null && (
                      <span className="text-[11px] text-muted-foreground ml-5">
                        耗时 {(h.duration_ms / 1000).toFixed(1)}s
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
