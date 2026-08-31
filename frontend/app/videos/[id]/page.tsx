"use client";

import { use, useCallback, useEffect, useState } from "react";
import { api, type QAReport, type Video } from "@/lib/api";
import { button, buttonDanger, card } from "@/lib/ui";
import { StateBadge } from "@/components/StateBadge";

export default function VideoDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const videoId = Number(id);

  const [video, setVideo] = useState<Video | null>(null);
  const [qaReport, setQaReport] = useState<QAReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(() => {
    api.getVideo(videoId).then(setVideo).catch((e) => setError(String(e)));
  }, [videoId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function run<T>(action: () => Promise<T>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (error && !video) return <p className="text-sm text-red-400">{error}</p>;
  if (!video) return <p className="text-sm text-neutral-500">Loading...</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold">
          #{video.id} {video.title ?? "(untitled)"}
        </h1>
        <StateBadge state={video.state} />
      </div>
      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className={`${card} flex flex-wrap gap-3`}>
        {video.state === "storyboard_ready" && (
          <button disabled={busy} className={button} onClick={() => run(() => api.renderVideo(video.id))}>
            Render
          </button>
        )}
        {video.state === "rendered" && (
          <button
            disabled={busy}
            className={button}
            onClick={() =>
              run(async () => {
                setQaReport(await api.qaVideo(video.id));
              })
            }
          >
            Run QA
          </button>
        )}
        {video.state === "qa_failed" && (
          <button disabled={busy} className={button} onClick={() => run(() => api.regenerateVideo(video.id))}>
            Regenerate storyboard
          </button>
        )}
        {video.state === "awaiting_approval" && (
          <>
            <button disabled={busy} className={button} onClick={() => run(() => api.approveVideo(video.id))}>
              Approve
            </button>
            <button
              disabled={busy}
              className={buttonDanger}
              onClick={() => run(() => api.rejectVideo(video.id))}
            >
              Reject
            </button>
          </>
        )}
        {["draft", "idea_selected", "published", "approved", "rejected", "failed"].includes(video.state) && (
          <span className="text-sm text-neutral-500">No action available in this state.</span>
        )}
      </div>

      {qaReport && (
        <div className={card}>
          <h2 className="mb-2 font-medium">QA report ({qaReport.passed ? "passed" : "failed"})</h2>
          <p className="text-sm text-neutral-400">
            Content score: {qaReport.content_score} ({qaReport.content_approved ? "approved" : "not approved"})
          </p>
          {qaReport.technical_issues.length > 0 && (
            <div className="mt-2">
              <div className="text-xs font-medium text-red-400">Technical issues</div>
              <ul className="list-inside list-disc text-sm text-neutral-400">
                {qaReport.technical_issues.map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            </div>
          )}
          {qaReport.content_issues.length > 0 && (
            <div className="mt-2">
              <div className="text-xs font-medium text-amber-400">Content issues</div>
              <ul className="list-inside list-disc text-sm text-neutral-400">
                {qaReport.content_issues.map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {video.rendered_path && (
        <div className={card}>
          <h2 className="mb-2 font-medium">Preview</h2>
          <video controls className="max-w-sm rounded" src={api.videoFileUrl(video.id)} />
        </div>
      )}

      <div className={card}>
        <h2 className="mb-2 font-medium">Scenes ({video.scenes.length})</h2>
        <ul className="space-y-3">
          {video.scenes.map((scene) => (
            <li key={scene.scene_number} className="border-b border-neutral-800 pb-2 text-sm last:border-0">
              <div className="font-medium">
                Scene {scene.scene_number} · {scene.duration_seconds}s · {scene.camera_motion}
              </div>
              <div className="text-neutral-400">{scene.narration}</div>
              <div className="text-neutral-500 italic">visual: {scene.visual_prompt}</div>
              <div className="text-neutral-500">caption: {scene.caption}</div>
            </li>
          ))}
          {video.scenes.length === 0 && <p className="text-sm text-neutral-500">No scenes yet.</p>}
        </ul>
      </div>
    </div>
  );
}
