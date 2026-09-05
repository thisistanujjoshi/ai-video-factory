const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export interface Niche {
  primary: string;
  secondary: string[];
}
export interface Audience {
  min_age: number;
  max_age: number;
  language: string;
}
export interface VideoConfig {
  type: string;
  min_duration_seconds: number;
  max_duration_seconds: number;
  aspect_ratio: string;
  resolution: string;
}
export interface Style {
  tone: string;
  pacing: string;
  narration: string;
  visual_style: string;
}
export interface Strategy {
  hook_types: string[];
}
export interface Publishing {
  youtube: boolean;
  instagram: boolean;
  tiktok: boolean;
}
export interface Schedule {
  videos_per_day: number;
}

export type AutomationMode = "manual" | "semi_automatic" | "autonomous";

export interface ContentProfile {
  id: number;
  name: string;
  niche: Niche;
  audience: Audience;
  video: VideoConfig;
  style: Style;
  strategy: Strategy;
  publishing: Publishing;
  schedule: Schedule;
  automation_mode: AutomationMode;
}

export interface IdeaScores {
  curiosity: number;
  emotion: number;
  trend: number;
  novelty: number;
  shareability: number;
  production_cost: number;
}

export interface Idea {
  id: number;
  content_profile_id: number;
  title: string;
  premise: string;
  hook: string;
  target_emotion: string;
  format: string;
  estimated_duration: number;
  difficulty: string;
  scores: IdeaScores;
  overall_score: number;
}

export interface Scene {
  scene_number: number;
  duration_seconds: number;
  narration: string;
  visual_prompt: string;
  camera_motion: string;
  caption: string;
  transition: string;
  sound_effect: string | null;
}

export type VideoState =
  | "draft"
  | "idea_selected"
  | "script_generating"
  | "script_ready"
  | "storyboard_generating"
  | "storyboard_ready"
  | "assets_generating"
  | "assets_ready"
  | "rendering"
  | "rendered"
  | "qa_pending"
  | "qa_failed"
  | "awaiting_approval"
  | "approved"
  | "scheduled"
  | "publishing"
  | "published"
  | "failed"
  | "rejected";

export interface Video {
  id: number;
  content_profile_id: number;
  idea_id: number | null;
  script_id: number | null;
  state: VideoState;
  title: string | null;
  rendered_path: string | null;
  scenes: Scene[];
}

export interface QAReport {
  video: Video;
  passed: boolean;
  technical_issues: string[];
  content_score: number;
  content_approved: boolean;
  content_issues: string[];
  content_recommendations: string[];
}

export type PublicationStatus = "pending" | "scheduled" | "publishing" | "published" | "failed";

export interface Publication {
  id: number;
  video_id: number;
  platform: string;
  status: PublicationStatus;
  platform_metadata: Record<string, unknown>;
  scheduled_for: string | null;
  published_at: string | null;
  platform_ref: string | null;
  error: string | null;
  retry_count: number;
}

export interface Metric {
  id: number;
  publication_id: number;
  platform: string;
  snapshot_label: string;
  collected_at: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  watch_time_seconds: number | null;
  retention_rate: number | null;
  followers_gained: number;
  engagement_rate: number;
}

export interface AnalyticsTotals {
  views: number;
  likes: number;
  comments: number;
  shares: number;
  followers_gained: number;
}

export interface VideoAnalytics {
  video_id: number;
  title: string | null;
  metrics: Metric[];
  totals: AnalyticsTotals;
}

export interface AutonomousCycleResult {
  video: Video;
  qa_passed: boolean;
  content_score: number;
  auto_published: boolean;
  publications: Publication[];
}

export interface ContentStrategy {
  id: number;
  content_profile_id: number;
  best_topics: string[];
  best_hook_types: string[];
  recommended_duration: { min_seconds: number; max_seconds: number };
  recommended_pacing: string;
  recommended_posting_windows: string[];
  avoid_patterns: string[];
  rationale: string;
  sample_size: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${init?.method ?? "GET"} ${path} failed (${response.status}): ${body}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  videoFileUrl: (id: number) => `${API_URL}/videos/${id}/file`,

  listProfiles: () => request<ContentProfile[]>("/content-profiles"),
  getProfile: (id: number) => request<ContentProfile>(`/content-profiles/${id}`),
  createProfile: (payload: Omit<ContentProfile, "id">) =>
    request<ContentProfile>("/content-profiles", { method: "POST", body: JSON.stringify(payload) }),
  updateProfile: (id: number, payload: Omit<ContentProfile, "id">) =>
    request<ContentProfile>(`/content-profiles/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteProfile: (id: number) => request<void>(`/content-profiles/${id}`, { method: "DELETE" }),
  generateStrategy: (id: number) =>
    request<ContentStrategy>(`/content-profiles/${id}/strategy/generate`, { method: "POST" }),
  getStrategy: (id: number) => request<ContentStrategy>(`/content-profiles/${id}/strategy`),
  runAutonomousCycle: (id: number) =>
    request<AutonomousCycleResult>(`/content-profiles/${id}/autonomous-cycle`, { method: "POST" }),

  generateIdeas: (contentProfileId: number, count = 10) =>
    request<Idea[]>("/ideas/generate", {
      method: "POST",
      body: JSON.stringify({ content_profile_id: contentProfileId, count }),
    }),
  listIdeas: (contentProfileId?: number) =>
    request<Idea[]>(`/ideas${contentProfileId ? `?content_profile_id=${contentProfileId}` : ""}`),

  generateVideo: (ideaId: number) =>
    request<Video>("/videos/generate", { method: "POST", body: JSON.stringify({ idea_id: ideaId }) }),
  listVideos: () => request<Video[]>("/videos"),
  getVideo: (id: number) => request<Video>(`/videos/${id}`),
  renderVideo: (id: number) => request<Video>(`/videos/${id}/render`, { method: "POST" }),
  retryVideo: (id: number) => request<Video>(`/videos/${id}/retry`, { method: "POST" }),
  qaVideo: (id: number) => request<QAReport>(`/videos/${id}/qa`, { method: "POST" }),
  regenerateVideo: (id: number) => request<Video>(`/videos/${id}/regenerate`, { method: "POST" }),
  approveVideo: (id: number) => request<Video>(`/videos/${id}/approve`, { method: "POST" }),
  rejectVideo: (id: number) => request<Video>(`/videos/${id}/reject`, { method: "POST" }),

  publishVideo: (id: number) => request<Publication[]>(`/videos/${id}/publish`, { method: "POST" }),
  scheduleVideo: (id: number, scheduledFor: string) =>
    request<Publication[]>(`/videos/${id}/schedule`, {
      method: "POST",
      body: JSON.stringify({ scheduled_for: scheduledFor }),
    }),
  listPublications: (videoId: number) => request<Publication[]>(`/videos/${videoId}/publications`),

  collectAnalytics: (videoId: number, snapshotLabel = "manual") =>
    request<Metric[]>(`/videos/${videoId}/analytics/collect?snapshot_label=${snapshotLabel}`, {
      method: "POST",
    }),
  listAnalytics: () => request<VideoAnalytics[]>("/analytics"),
  getVideoAnalytics: (videoId: number) => request<VideoAnalytics>(`/analytics/videos/${videoId}`),
};
