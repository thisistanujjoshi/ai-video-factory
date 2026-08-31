import { card } from "@/lib/ui";

export default function AnalyticsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Analytics</h1>
      <div className={card}>
        <p className="text-sm text-neutral-400">
          Not implemented yet — metrics collection, platform normalization, and this dashboard land in
          Phase 7, once Phase 6 publishing exists to produce data to collect.
        </p>
      </div>
    </div>
  );
}
