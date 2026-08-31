"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Video } from "@/lib/api";
import { card } from "@/lib/ui";
import { StateBadge } from "@/components/StateBadge";

export default function VideosPage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listVideos().then(setVideos).catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Videos</h1>
      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className={card}>
        <ul className="divide-y divide-neutral-800">
          {videos.map((v) => (
            <li key={v.id} className="flex items-center justify-between py-2 text-sm">
              <Link href={`/videos/${v.id}`} className="hover:underline">
                #{v.id} {v.title ?? "(untitled)"}
              </Link>
              <StateBadge state={v.state} />
            </li>
          ))}
          {videos.length === 0 && <li className="py-2 text-sm text-neutral-500">No videos yet.</li>}
        </ul>
      </div>
    </div>
  );
}
