export interface Run {
  run_id: string;
  pipeline_name: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  updated_at?: string;
  state?: PipelineState;
}

export interface PipelineState {
  run_id: string;
  pipeline_name: string;
  user_brief: UserBrief;
  topics: Topic[];
  selected_topic?: Topic;
  materials: Material[];
  contents: Record<string, PlatformContent>;
  reviews: Record<string, ReviewResult>;
  analysis?: Analysis;
  stage: string;
  errors: PipelineError[];
}

export interface UserBrief {
  topic: string;
  keywords: string[];
  platform_hints: string[];
  style: string;
}

export interface Topic {
  title: string;
  angle: string;
  score: number;
  reasoning: string;
}

export interface Material {
  source: string;
  title: string;
  snippet: string;
  source_type: string;
}

export interface PlatformContent {
  platform: string;
  title: string;
  body: string;
  tags: string[];
  image_paths: string[];
  image_prompts: string[];
}

export interface ReviewResult {
  platform: string;
  passed: boolean;
  score: number;
  issues: string[];
  suggestions: string[];
}

export interface Analysis {
  summary: string;
  insights: string[];
  improvement_suggestions: string[];
}

export interface PipelineError {
  agent: string;
  error_type: string;
  message: string;
  recoverable: boolean;
}

export interface Pipeline {
  name: string;
  description: string;
  platforms: string[];
  stages: number;
  file: string;
}

export interface StageConfig {
  agent: string;
  config: Record<string, any>;
  on_error?: string;
  retry_count?: number;
}

export interface PipelineDetail {
  name: string;
  description: string;
  platforms: string[];
  stages: StageConfig[];
}

export interface Content {
  content_id: string;
  run_id: string;
  platform: string;
  title: string;
  body: string;
  tags: string[];
  image_paths: string[];
  image_prompts?: string[];
  status: string;
  publish_url?: string;
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
