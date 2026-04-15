export interface PipelineRun {
  run_id: string;
  pipeline_name: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  updated_at: string;
}

export interface Content {
  content_id: string;
  run_id: string;
  platform: string;
  title: string;
  body: string;
  tags: string[];
  status: "pending_review" | "approved" | "rejected" | "published";
  created_at: string;
}

export interface PipelineStage {
  agent: string;
  status: "pending" | "running" | "completed" | "failed";
  output_summary?: string;
}

export interface PipelineEvent {
  type: "stage_started" | "stage_completed" | "stage_failed" | "pipeline_completed";
  agent?: string;
  timestamp: string;
  output_summary?: string;
  error?: string;
}
