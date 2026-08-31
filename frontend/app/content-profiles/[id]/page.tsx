"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type ContentProfile, type ContentStrategy } from "@/lib/api";
import { button, buttonDanger, card, input, label } from "@/lib/ui";

export default function ContentProfileDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const profileId = Number(id);
  const router = useRouter();

  const [profile, setProfile] = useState<ContentProfile | null>(null);
  const [strategy, setStrategy] = useState<ContentStrategy | null>(null);
  const [ideaCount, setIdeaCount] = useState(10);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generatingStrategy, setGeneratingStrategy] = useState(false);

  useEffect(() => {
    api.getProfile(profileId).then(setProfile).catch((e) => setError(String(e)));
    api.getStrategy(profileId).then(setStrategy).catch(() => setStrategy(null));
  }, [profileId]);

  async function onGenerateIdeas() {
    setGenerating(true);
    setError(null);
    try {
      await api.generateIdeas(profileId, ideaCount);
      router.push(`/ideas?profile=${profileId}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setGenerating(false);
    }
  }

  async function onGenerateStrategy() {
    setGeneratingStrategy(true);
    setError(null);
    try {
      setStrategy(await api.generateStrategy(profileId));
    } catch (e) {
      setError(String(e));
    } finally {
      setGeneratingStrategy(false);
    }
  }

  async function onDelete() {
    if (!confirm("Delete this content profile?")) return;
    await api.deleteProfile(profileId);
    router.push("/content-profiles");
  }

  if (error) return <p className="text-sm text-red-400">{error}</p>;
  if (!profile) return <p className="text-sm text-neutral-500">Loading...</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{profile.name}</h1>
        <button onClick={onDelete} className={buttonDanger}>
          Delete
        </button>
      </div>

      <div className={`${card} grid grid-cols-2 gap-4 text-sm`}>
        <div>
          <div className={label}>Niche</div>
          {profile.niche.primary} ({profile.niche.secondary.join(", ") || "—"})
        </div>
        <div>
          <div className={label}>Audience</div>
          {profile.audience.min_age}-{profile.audience.max_age}, {profile.audience.language}
        </div>
        <div>
          <div className={label}>Video</div>
          {profile.video.min_duration_seconds}-{profile.video.max_duration_seconds}s,{" "}
          {profile.video.aspect_ratio}, {profile.video.resolution}
        </div>
        <div>
          <div className={label}>Style</div>
          {profile.style.tone}, {profile.style.pacing} pacing, {profile.style.narration} narration,{" "}
          {profile.style.visual_style}
        </div>
        <div>
          <div className={label}>Hook types</div>
          {profile.strategy.hook_types.join(", ") || "—"}
        </div>
        <div>
          <div className={label}>Publishing</div>
          {Object.entries(profile.publishing)
            .filter(([, v]) => v)
            .map(([k]) => k)
            .join(", ") || "none"}
        </div>
      </div>

      <div className={`${card} space-y-3`}>
        <div className="flex items-center justify-between">
          <h2 className="font-medium">Content strategy</h2>
          <button onClick={onGenerateStrategy} disabled={generatingStrategy} className={button}>
            {generatingStrategy ? "Generating..." : "Regenerate from history"}
          </button>
        </div>
        {strategy ? (
          <div className="space-y-2 text-sm">
            <p className="text-neutral-500">
              Based on {strategy.sample_size} published video{strategy.sample_size === 1 ? "" : "s"}.
            </p>
            <p>
              <span className={label}>Best topics</span>
              {strategy.best_topics.join(", ") || "—"}
            </p>
            <p>
              <span className={label}>Best hook types</span>
              {strategy.best_hook_types.join(", ") || "—"}
            </p>
            <p>
              <span className={label}>Recommended duration</span>
              {strategy.recommended_duration.min_seconds}-{strategy.recommended_duration.max_seconds}s,{" "}
              {strategy.recommended_pacing} pacing
            </p>
            <p>
              <span className={label}>Avoid</span>
              {strategy.avoid_patterns.join(", ") || "—"}
            </p>
            <p className="text-neutral-500 italic">{strategy.rationale}</p>
          </div>
        ) : (
          <p className="text-sm text-neutral-500">
            No strategy generated yet. Future idea generation uses whatever strategy is current.
          </p>
        )}
      </div>

      <div className={`${card} space-y-3`}>
        <h2 className="font-medium">Generate ideas</h2>
        <div className="flex items-center gap-3">
          <input
            type="number"
            className={`${input} w-24`}
            value={ideaCount}
            onChange={(e) => setIdeaCount(Number(e.target.value))}
          />
          <button onClick={onGenerateIdeas} disabled={generating} className={button}>
            {generating ? "Generating..." : "Generate ideas"}
          </button>
        </div>
      </div>
    </div>
  );
}
