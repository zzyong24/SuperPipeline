"use client";

import { useState } from "react";

interface ContentCardProps {
  content: {
    content_id: string;
    platform: string;
    title: string;
    body: string;
    tags: string[];
    status: string;
  };
}

export function ContentCard({ content }: ContentCardProps) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    const text = `${content.title}\n\n${content.body}\n\n${content.tags.map((t) => `#${t}`).join(" ")}`;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <div className="flex justify-between items-start">
        <div>
          <span className="text-xs font-medium px-2 py-0.5 bg-blue-100 text-blue-800 rounded">{content.platform}</span>
          <span className="ml-2 text-xs text-gray-400">{content.status}</span>
        </div>
        <button onClick={copyToClipboard} className="px-3 py-1 text-sm bg-gray-900 text-white rounded hover:bg-gray-700">
          {copied ? "✓ Copied" : "Copy"}
        </button>
      </div>
      <h3 className="font-medium">{content.title}</h3>
      <p className="text-sm text-gray-600 whitespace-pre-wrap line-clamp-6">{content.body}</p>
      {content.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {content.tags.map((tag) => (<span key={tag} className="text-xs text-blue-600">#{tag}</span>))}
        </div>
      )}
    </div>
  );
}
