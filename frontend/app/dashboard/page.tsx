"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type ContentProfile, type Video, type VideoState } from "@/lib/api";
import { card } from "@/lib/ui";
import { StateBadge } from "@/components/StateBadge";

const GENERATING: VideoState[] = [
  "script_generating",
  "storyboard_generating",
  "assets_generating",
  "rendering",
  "qa_pending",
];
const FAILED: VideoState[] = ["failed", "qa_failed", "rejected"];

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className={card}>
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-sm text-neutral-400">{label}</div>
    </div>
  );
}

export default function DashboardPage() {
  const [profiles, setProfiles] = useState<ContentProfile[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.listProfiles(), api.listVideos()])
      .then(([p, v]) => {
        setProfiles(p);
        setVideos(v);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const published = videos.filter((v) => v.state === "published").length;
  const pendingApproval = videos.filter((v) => v.state === "awaiting_approval").length;
  const generating = videos.filter((v) => GENERATING.includes(v.state)).length;
  const failedCount = videos.filter((v) => FAILED.includes(v.state)).length;

  return (
    <div className="space-y-8">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Content profiles" value={profiles.length} />
        <Stat label="Videos total" value={videos.length} />
        <Stat label="Published" value={published} />
        <Stat label="Pending approval" value={pendingApproval} />
        <Stat label="Currently generating" value={generating} />
        <Stat label="Failed / rejected" value={failedCount} />
      </div>

      <div className={card}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-medium">Recent videos</h2>
          <Link href="/videos" className="text-sm text-neutral-400 hover:text-neutral-100">
            View all
          </Link>
        </div>
        {videos.length === 0 ? (
          <p className="text-sm text-neutral-500">
            No videos yet. Start from a{" "}
            <Link href="/content-profiles" className="underline">
              content profile
            </Link>
            .
          </p>
        ) : (
          <ul className="divide-y divide-neutral-800">
            {videos.slice(0, 8).map((v) => (
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
    </div>
  );
}
