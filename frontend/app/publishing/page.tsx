"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Publication, type Video } from "@/lib/api";
import { card } from "@/lib/ui";

const RELEVANT_STATES: Video["state"][] = ["approved", "scheduled", "publishing", "published", "failed"];

export default function PublishingPage() {
  const [rows, setRows] = useState<{ video: Video; publications: Publication[] }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listVideos()
      .then(async (videos) => {
        const candidates = videos.filter((v) => RELEVANT_STATES.includes(v.state));
        const withPubs = await Promise.all(
          candidates.map(async (video) => ({
            video,
            publications: await api.listPublications(video.id).catch(() => []),
          }))
        );
        setRows(withPubs.filter((r) => r.publications.length > 0));
      })
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Publishing</h1>
      <p className="text-sm text-neutral-500">
        Real publish/schedule pipeline (Phase 6), running against mocked platform publishers — no
        YouTube/Instagram/TikTok account is actually connected. Publish or schedule a video from its detail
        page once it&apos;s approved.
      </p>
      {error && <p className="text-sm text-red-400">{error}</p>}

      {rows.length === 0 ? (
        <div className={card}>
          <p className="text-sm text-neutral-500">No publish attempts yet.</p>
        </div>
      ) : (
        rows.map(({ video, publications }) => (
          <div key={video.id} className={card}>
            <Link href={`/videos/${video.id}`} className="font-medium hover:underline">
              #{video.id} {video.title ?? "(untitled)"}
            </Link>
            <ul className="mt-2 divide-y divide-neutral-800">
              {publications.map((pub) => (
                <li key={pub.id} className="flex items-center justify-between py-2 text-sm">
                  <span className="capitalize">{pub.platform}</span>
                  <span className="text-neutral-400">{pub.status}</span>
                  <span className="truncate text-neutral-500">{pub.platform_ref ?? pub.error ?? "—"}</span>
                </li>
              ))}
            </ul>
          </div>
        ))
      )}
    </div>
  );
}
