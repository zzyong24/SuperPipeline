import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SuperPipeline",
  description: "Content production pipeline dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body className="bg-white text-gray-900">{children}</body>
    </html>
  );
}
