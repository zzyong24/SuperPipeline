import { Camera } from "lucide-react";

export function ImagePlaceholder({ prompt }: { prompt?: string }) {
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
