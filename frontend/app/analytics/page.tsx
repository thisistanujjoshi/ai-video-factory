"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type VideoAnalytics } from "@/lib/api";
import { card } from "@/lib/ui";

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-lg font-semibold">{value.toLocaleString()}</div>
      <div className="text-xs text-neutral-500">{label}</div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [rows, setRows] = useState<VideoAnalytics[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => api.listAnalytics().then(setRows).catch((e) => setError(String(e)));

  useEffect(() => {
    refresh();
  }, []);

  const grandTotals = rows.reduce(
    (acc, row) => ({
      views: acc.views + row.totals.views,
      likes: acc.likes + row.totals.likes,
      comments: acc.comments + row.totals.comments,
      shares: acc.shares + row.totals.shares,
      followers_gained: acc.followers_gained + row.totals.followers_gained,
    }),
    { views: 0, likes: 0, comments: 0, shares: 0, followers_gained: 0 }
  );

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Analytics</h1>
      <p className="text-sm text-neutral-500">
        Metrics are collected on demand (Phase 7) from mocked platform collectors — no real YouTube/
        Instagram/TikTok account is connected, so numbers are plausible but not real. Collect a snapshot from
        a video&apos;s detail page once it&apos;s published.
      </p>
      {error && <p className="text-sm text-red-400">{error}</p>}

      {rows.length > 0 && (
        <div className={`${card} grid grid-cols-2 gap-4 sm:grid-cols-5`}>
          <Stat label="Total views" value={grandTotals.views} />
          <Stat label="Total likes" value={grandTotals.likes} />
          <Stat label="Total comments" value={grandTotals.comments} />
          <Stat label="Total shares" value={grandTotals.shares} />
          <Stat label="Followers gained" value={grandTotals.followers_gained} />
        </div>
      )}

      {rows.length === 0 ? (
        <div className={card}>
          <p className="text-sm text-neutral-500">No metrics collected yet.</p>
        </div>
      ) : (
        rows.map((row) => (
          <div key={row.video_id} className={card}>
            <Link href={`/videos/${row.video_id}`} className="font-medium hover:underline">
              #{row.video_id} {row.title ?? "(untitled)"}
            </Link>
            <div className="mt-2 grid grid-cols-2 gap-4 sm:grid-cols-5">
              <Stat label="Views" value={row.totals.views} />
              <Stat label="Likes" value={row.totals.likes} />
              <Stat label="Comments" value={row.totals.comments} />
              <Stat label="Shares" value={row.totals.shares} />
              <Stat label="Followers" value={row.totals.followers_gained} />
            </div>
            <ul className="mt-3 divide-y divide-neutral-800 text-sm">
              {row.metrics.map((m) => (
                <li key={m.id} className="flex items-center justify-between py-1.5">
                  <span className="capitalize">{m.platform}</span>
                  <span className="text-neutral-500">{m.snapshot_label} snapshot</span>
                  <span className="text-neutral-400">{(m.engagement_rate * 100).toFixed(1)}% engagement</span>
                </li>
              ))}
            </ul>
          </div>
        ))
      )}
    </div>
  );
}
