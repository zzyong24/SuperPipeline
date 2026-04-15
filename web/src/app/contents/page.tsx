"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { Content } from "@/lib/types";
import { ContentPreview } from "@/components/contents/ContentPreview";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Copy, CheckCircle2 } from "lucide-react";

export default function ContentsPage() {
  const [contents, setContents] = useState<Content[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState<Content | null>(null);

  useEffect(() => {
    setLoading(true);
    const params = filter === "all" ? {} : { status: filter };
    api
      .listContents(params)
      .then(setContents)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filter]);

  function handleApprove(contentId: string) {
    api
      .approveContent(contentId)
      .then(() => {
        setContents((prev) =>
          prev.map((c) =>
            c.content_id === contentId ? { ...c, status: "approved" } : c
          )
        );
        if (selected?.content_id === contentId) {
          setSelected((prev) => (prev ? { ...prev, status: "approved" } : null));
        }
      })
      .catch(() => {});
  }

  function handleCopy(content: Content) {
    navigator.clipboard.writeText(`${content.title}\n\n${content.body}`);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">内容库</h1>
      </div>

      <Tabs value={filter} onValueChange={setFilter}>
        <TabsList>
          <TabsTrigger value="all" className="text-[13px]">全部</TabsTrigger>
          <TabsTrigger value="approved" className="text-[13px]">已通过</TabsTrigger>
          <TabsTrigger value="pending_review" className="text-[13px]">待审核</TabsTrigger>
          <TabsTrigger value="published" className="text-[13px]">已发布</TabsTrigger>
        </TabsList>
      </Tabs>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-72" />
          ))}
        </div>
      ) : contents.length === 0 ? (
        <p className="text-sm text-muted-foreground">暂无内容</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {contents.map((c) => (
            <ContentPreview
              key={c.content_id}
              content={c}
              onClick={() => setSelected(c)}
            />
          ))}
        </div>
      )}

      {/* Detail Dialog */}
      <Dialog open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          {selected && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-2">
                  <DialogTitle className="text-base">{selected.title}</DialogTitle>
                  <Badge variant="outline" className="text-[10px]">
                    {selected.platform}
                  </Badge>
                </div>
              </DialogHeader>
              <div className="space-y-4 mt-2">
                <p className="text-[13px] text-muted-foreground whitespace-pre-line leading-relaxed">
                  {selected.body}
                </p>
                {selected.tags?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {selected.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-[10px]">
                        #{tag}
                      </Badge>
                    ))}
                  </div>
                )}
                <div className="flex items-center gap-2 pt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-1.5 text-[12px]"
                    onClick={() => handleCopy(selected)}
                  >
                    <Copy className="h-3 w-3" /> 复制
                  </Button>
                  {selected.status === "pending_review" && (
                    <Button
                      size="sm"
                      className="gap-1.5 text-[12px]"
                      onClick={() => handleApprove(selected.content_id)}
                    >
                      <CheckCircle2 className="h-3 w-3" /> 通过
                    </Button>
                  )}
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
