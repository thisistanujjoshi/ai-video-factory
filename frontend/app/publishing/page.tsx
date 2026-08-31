import { card } from "@/lib/ui";

export default function PublishingPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Publishing</h1>
      <div className={card}>
        <p className="text-sm text-neutral-400">
          Not implemented yet — publisher interfaces, YouTube/Instagram/TikTok integrations, and scheduling
          land in Phase 6. Approved videos currently stop at the <code>approved</code> state.
        </p>
      </div>
    </div>
  );
}
