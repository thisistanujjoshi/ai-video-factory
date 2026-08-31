"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, type Idea } from "@/lib/api";
import { button, card } from "@/lib/ui";

function IdeasContent() {
  const searchParams = useSearchParams();
  const profileParam = searchParams.get("profile");
  const profileId = profileParam ? Number(profileParam) : undefined;
  const router = useRouter();

  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [creatingVideoFor, setCreatingVideoFor] = useState<number | null>(null);

  useEffect(() => {
    api.listIdeas(profileId).then(setIdeas).catch((e) => setError(String(e)));
  }, [profileId]);

  async function onCreateVideo(ideaId: number) {
    setCreatingVideoFor(ideaId);
    setError(null);
    try {
      const video = await api.generateVideo(ideaId);
      router.push(`/videos/${video.id}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setCreatingVideoFor(null);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">
        Ideas{profileId ? ` for profile #${profileId}` : ""}
      </h1>
      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="space-y-3">
        {ideas
          .slice()
          .sort((a, b) => b.overall_score - a.overall_score)
          .map((idea) => (
            <div key={idea.id} className={card}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="font-medium">{idea.title}</h3>
                  <p className="mt-1 text-sm text-neutral-400">{idea.premise}</p>
                  <p className="mt-1 text-sm italic text-neutral-500">&ldquo;{idea.hook}&rdquo;</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-2">
                  <span className="text-lg font-semibold">{idea.overall_score.toFixed(1)}</span>
                  <button
                    onClick={() => onCreateVideo(idea.id)}
                    disabled={creatingVideoFor === idea.id}
                    className={button}
                  >
                    {creatingVideoFor === idea.id ? "Creating..." : "Create video"}
                  </button>
                </div>
              </div>
            </div>
          ))}
        {ideas.length === 0 && (
          <p className="text-sm text-neutral-500">
            No ideas yet. Generate some from a content profile page.
          </p>
        )}
      </div>
    </div>
  );
}

export default function IdeasPage() {
  return (
    <Suspense fallback={<p className="text-sm text-neutral-500">Loading...</p>}>
      <IdeasContent />
    </Suspense>
  );
}
