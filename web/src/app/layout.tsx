import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "SuperPipeline",
  description: "Content production pipeline workstation",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh" suppressHydrationWarning>
      <body className="bg-background text-foreground antialiased">
        <Sidebar />
        <main className="ml-60 min-h-screen">
          <div className="p-6 max-w-[1200px]">{children}</div>
        </main>
      </body>
    </html>
  );
}
