import type { VideoState } from "@/lib/api";

const COLORS: Record<string, string> = {
  draft: "bg-neutral-700 text-neutral-100",
  idea_selected: "bg-neutral-700 text-neutral-100",
  script_generating: "bg-amber-800 text-amber-100",
  script_ready: "bg-amber-800 text-amber-100",
  storyboard_generating: "bg-amber-800 text-amber-100",
  storyboard_ready: "bg-blue-800 text-blue-100",
  assets_generating: "bg-amber-800 text-amber-100",
  assets_ready: "bg-blue-800 text-blue-100",
  rendering: "bg-amber-800 text-amber-100",
  rendered: "bg-blue-800 text-blue-100",
  qa_pending: "bg-amber-800 text-amber-100",
  qa_failed: "bg-red-900 text-red-100",
  awaiting_approval: "bg-purple-800 text-purple-100",
  approved: "bg-green-800 text-green-100",
  scheduled: "bg-green-800 text-green-100",
  publishing: "bg-amber-800 text-amber-100",
  published: "bg-green-900 text-green-100",
  failed: "bg-red-900 text-red-100",
  rejected: "bg-red-900 text-red-100",
};

export function StateBadge({ state }: { state: VideoState }) {
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${COLORS[state] ?? "bg-neutral-700 text-neutral-100"}`}>
      {state.replace(/_/g, " ")}
    </span>
  );
}
