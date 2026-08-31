"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Video, type VideoState } from "@/lib/api";
import { card } from "@/lib/ui";
import { StateBadge } from "@/components/StateBadge";

const GENERATING: VideoState[] = [
  "idea_selected",
  "script_generating",
  "storyboard_generating",
  "assets_generating",
  "rendering",
  "qa_pending",
];
const FAILED: VideoState[] = ["failed", "qa_failed", "rejected"];

function Bucket({ title, videos }: { title: string; videos: Video[] }) {
  return (
    <div className={card}>
      <h2 className="mb-2 font-medium">
        {title} <span className="text-neutral-500">({videos.length})</span>
      </h2>
      {videos.length === 0 ? (
        <p className="text-sm text-neutral-500">Nothing here.</p>
      ) : (
        <ul className="divide-y divide-neutral-800">
          {videos.map((v) => (
            <li key={v.id} className="flex items-center justify-between py-2 text-sm">
              <Link href={`/videos/${v.id}`} className="hover:underline">
                #{v.id} {v.title ?? "(untitled)"}
              </Link>
              <StateBadge state={v.state} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function QueuePage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listVideos().then(setVideos).catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Queue</h1>
      <p className="text-sm text-neutral-500">
        Derived from the video list — no separate backend queue endpoint (job status/progress tracking is
        Phase 9&apos;s autonomous-mode territory; this MVP runs each pipeline step synchronously on request).
      </p>
      {error && <p className="text-sm text-red-400">{error}</p>}

      <Bucket title="Currently generating" videos={videos.filter((v) => GENERATING.includes(v.state))} />
      <Bucket title="Pending approval" videos={videos.filter((v) => v.state === "awaiting_approval")} />
      <Bucket title="Scheduled" videos={videos.filter((v) => v.state === "scheduled")} />
      <Bucket title="Failed / rejected" videos={videos.filter((v) => FAILED.includes(v.state))} />
    </div>
  );
}
