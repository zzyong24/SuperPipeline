"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ImagePlaceholder } from "./ImagePlaceholder";
import { Copy } from "lucide-react";
import type { Content } from "@/lib/types";

const STATUS_LABELS: Record<string, string> = {
  approved: "已通过",
  published: "已发布",
  pending_review: "待审核",
  draft: "草稿",
};

interface ContentPreviewProps {
  content: Content;
  onClick?: () => void;
}

export function ContentPreview({ content, onClick }: ContentPreviewProps) {
  const firstPath = content.image_paths?.[0];
  const firstPrompt = content.image_prompts?.[0];

  function handleCopy(e: React.MouseEvent) {
    e.stopPropagation();
    navigator.clipboard.writeText(`${content.title}\n\n${content.body}`);
  }

  return (
    <Card
      className="cursor-pointer hover:shadow-sm transition-shadow overflow-hidden"
      onClick={onClick}
    >
      <ImagePlaceholder src={firstPath} prompt={firstPrompt} />
      <CardContent className="p-4 space-y-2">
        <h3 className="font-medium text-sm leading-tight line-clamp-2">
          {content.title}
        </h3>
        <p className="text-[12px] text-muted-foreground line-clamp-4 leading-relaxed">
          {content.body}
        </p>
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-1.5">
            <Badge variant="outline" className="text-[10px]">
              {content.platform}
            </Badge>
            <Badge
              variant="outline"
              className={
                content.status === "approved"
                  ? "text-[10px] bg-emerald-50 text-emerald-700 border-emerald-200"
                  : content.status === "published"
                  ? "text-[10px] bg-blue-50 text-blue-700 border-blue-200"
                  : "text-[10px]"
              }
            >
              {STATUS_LABELS[content.status] || content.status.replace("_", " ")}
            </Badge>
          </div>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 w-7 p-0"
            onClick={handleCopy}
          >
            <Copy className="h-3.5 w-3.5" />
          </Button>
        </div>
        {content.tags?.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {content.tags.slice(0, 4).map((tag) => (
              <span key={tag} className="text-[10px] text-muted-foreground">
                #{tag}
              </span>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
