import { Camera } from "lucide-react";

interface ImagePlaceholderProps {
  src?: string;
  prompt?: string;
}

export function ImagePlaceholder({ src, prompt }: ImagePlaceholderProps) {
  if (src) {
    return (
      <div className="h-40 bg-muted rounded-md overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={prompt || "content image"}
          className="w-full h-full object-cover"
          onError={(e) => {
            // Fallback to placeholder if image fails to load
            const target = e.currentTarget as HTMLImageElement;
            target.style.display = "none";
            const parent = target.parentElement;
            if (parent) {
              parent.classList.add("flex", "flex-col", "items-center", "justify-center", "gap-2", "px-4");
              const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
              icon.setAttribute("class", "h-5 w-5 text-muted-foreground/50");
              icon.setAttribute("viewBox", "0 0 24 24");
              icon.setAttribute("fill", "none");
              icon.setAttribute("stroke", "currentColor");
              icon.setAttribute("stroke-width", "2");
              const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
              use.setAttribute("href", "#camera-icon");
              icon.appendChild(use);
              const p = document.createElement("p");
              p.className = "text-[11px] text-muted-foreground italic text-center line-clamp-3";
              p.textContent = prompt || "";
              parent.innerHTML = '<svg class="h-5 w-5 text-muted-foreground/50" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><Camera class="h-5 w-5" /></svg>';
              parent.appendChild(p);
            }
          }}
        />
      </div>
    );
  }

  return (
    <div className="h-40 bg-muted rounded-md flex flex-col items-center justify-center gap-2 px-4">
      <Camera className="h-5 w-5 text-muted-foreground/50" />
      {prompt && (
        <p className="text-[11px] text-muted-foreground italic text-center line-clamp-3">
          {prompt}
        </p>
      )}
    </div>
  );
}
