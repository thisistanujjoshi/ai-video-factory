"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type ContentProfile } from "@/lib/api";
import { button, card, input, label } from "@/lib/ui";

const DEFAULT_FORM = {
  name: "",
  nichePrimary: "",
  nicheSecondary: "",
  minAge: 18,
  maxAge: 35,
  language: "English",
  minDuration: 45,
  maxDuration: 75,
  aspectRatio: "9:16",
  resolution: "1080x1920",
  tone: "",
  pacing: "fast",
  narration: "dramatic",
  visualStyle: "cinematic",
  hookTypes: "curiosity, question",
};

export default function ContentProfilesPage() {
  const [profiles, setProfiles] = useState<ContentProfile[]>([]);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const refresh = () => api.listProfiles().then(setProfiles).catch((e) => setError(String(e)));

  useEffect(() => {
    refresh();
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.createProfile({
        name: form.name,
        niche: {
          primary: form.nichePrimary,
          secondary: form.nicheSecondary.split(",").map((s) => s.trim()).filter(Boolean),
        },
        audience: { min_age: form.minAge, max_age: form.maxAge, language: form.language },
        video: {
          type: "short",
          min_duration_seconds: form.minDuration,
          max_duration_seconds: form.maxDuration,
          aspect_ratio: form.aspectRatio,
          resolution: form.resolution,
        },
        style: {
          tone: form.tone,
          pacing: form.pacing,
          narration: form.narration,
          visual_style: form.visualStyle,
        },
        strategy: { hook_types: form.hookTypes.split(",").map((s) => s.trim()).filter(Boolean) },
        publishing: { youtube: true, instagram: true, tiktok: true },
        schedule: { videos_per_day: 1 },
      });
      setForm(DEFAULT_FORM);
      refresh();
    } catch (err) {
      setError(String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-8">
      <h1 className="text-xl font-semibold">Content Profiles</h1>
      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className={card}>
        <ul className="divide-y divide-neutral-800">
          {profiles.map((p) => (
            <li key={p.id} className="flex items-center justify-between py-2 text-sm">
              <Link href={`/content-profiles/${p.id}`} className="hover:underline">
                {p.name}
              </Link>
              <span className="text-neutral-500">{p.niche.primary}</span>
            </li>
          ))}
          {profiles.length === 0 && <li className="py-2 text-sm text-neutral-500">No profiles yet.</li>}
        </ul>
      </div>

      <form onSubmit={onSubmit} className={`${card} space-y-4`}>
        <h2 className="font-medium">New content profile</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={label}>Name</label>
            <input
              className={input}
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div>
            <label className={label}>Primary niche</label>
            <input
              className={input}
              required
              value={form.nichePrimary}
              onChange={(e) => setForm({ ...form, nichePrimary: e.target.value })}
            />
          </div>
          <div>
            <label className={label}>Secondary niches (comma separated)</label>
            <input
              className={input}
              value={form.nicheSecondary}
              onChange={(e) => setForm({ ...form, nicheSecondary: e.target.value })}
            />
          </div>
          <div>
            <label className={label}>Tone</label>
            <input
              className={input}
              required
              value={form.tone}
              onChange={(e) => setForm({ ...form, tone: e.target.value })}
            />
          </div>
          <div>
            <label className={label}>Audience age range</label>
            <div className="flex gap-2">
              <input
                type="number"
                className={input}
                value={form.minAge}
                onChange={(e) => setForm({ ...form, minAge: Number(e.target.value) })}
              />
              <input
                type="number"
                className={input}
                value={form.maxAge}
                onChange={(e) => setForm({ ...form, maxAge: Number(e.target.value) })}
              />
            </div>
          </div>
          <div>
            <label className={label}>Duration range (seconds)</label>
            <div className="flex gap-2">
              <input
                type="number"
                className={input}
                value={form.minDuration}
                onChange={(e) => setForm({ ...form, minDuration: Number(e.target.value) })}
              />
              <input
                type="number"
                className={input}
                value={form.maxDuration}
                onChange={(e) => setForm({ ...form, maxDuration: Number(e.target.value) })}
              />
            </div>
          </div>
          <div>
            <label className={label}>Resolution</label>
            <input
              className={input}
              value={form.resolution}
              onChange={(e) => setForm({ ...form, resolution: e.target.value })}
            />
          </div>
          <div>
            <label className={label}>Aspect ratio</label>
            <input
              className={input}
              value={form.aspectRatio}
              onChange={(e) => setForm({ ...form, aspectRatio: e.target.value })}
            />
          </div>
          <div>
            <label className={label}>Pacing</label>
            <input
              className={input}
              value={form.pacing}
              onChange={(e) => setForm({ ...form, pacing: e.target.value })}
            />
          </div>
          <div>
            <label className={label}>Narration style</label>
            <input
              className={input}
              value={form.narration}
              onChange={(e) => setForm({ ...form, narration: e.target.value })}
            />
          </div>
          <div>
            <label className={label}>Visual style</label>
            <input
              className={input}
              value={form.visualStyle}
              onChange={(e) => setForm({ ...form, visualStyle: e.target.value })}
            />
          </div>
          <div>
            <label className={label}>Hook types (comma separated)</label>
            <input
              className={input}
              value={form.hookTypes}
              onChange={(e) => setForm({ ...form, hookTypes: e.target.value })}
            />
          </div>
        </div>
        <button type="submit" disabled={submitting} className={button}>
          {submitting ? "Creating..." : "Create profile"}
        </button>
      </form>
    </div>
  );
}
