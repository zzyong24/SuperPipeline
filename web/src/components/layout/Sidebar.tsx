"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Play,
  FileText,
  Plus,
  Workflow,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { api } from "@/lib/api-client";
import type { Pipeline } from "@/lib/types";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "仪表盘", icon: LayoutDashboard },
  { href: "/runs", label: "运行记录", icon: Play },
  { href: "/contents", label: "内容库", icon: FileText },
];

export function Sidebar() {
  const pathname = usePathname();
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);

  useEffect(() => {
    api.listPipelines().then(setPipelines).catch(() => {});
  }, []);

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-60 bg-[var(--sidebar)] border-r border-border flex flex-col z-30">
      {/* Logo */}
      <div className="h-14 flex items-center px-5 border-b border-border">
        <Workflow className="h-5 w-5 mr-2 text-foreground" />
        <span className="font-semibold text-sm tracking-tight">SuperPipeline</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-3 space-y-0.5">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-[13px] font-medium transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}

        <Separator className="!my-3" />

        <Link href="/new">
          <Button size="sm" className="w-full justify-start gap-2 text-[13px]">
            <Plus className="h-4 w-4" />
            新建运行
          </Button>
        </Link>
      </nav>

      {/* Pipelines section */}
      {pipelines.length > 0 && (
        <div className="px-3 pb-4">
          <Separator className="mb-3" />
          <p className="px-2.5 text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-2">
            管道列表
          </p>
          <div className="space-y-0.5">
            {pipelines.map((p) => (
              <Link
                key={p.name}
                href={`/new?pipeline=${encodeURIComponent(p.file)}`}
                className="flex items-center gap-2 px-2.5 py-1.5 text-[12px] text-muted-foreground rounded-md hover:bg-accent/50 hover:text-foreground transition-colors cursor-pointer"
              >
                <ChevronRight className="h-3 w-3" />
                <span className="truncate">{p.name}</span>
                <span className="ml-auto text-[10px] text-muted-foreground/60">
                  {p.platforms.length}p
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}
