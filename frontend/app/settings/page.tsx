import { card } from "@/lib/ui";

const PROVIDERS = [
  { name: "LLM", env: "LLM_PROVIDER", current: "mock" },
  { name: "Image", env: "IMAGE_PROVIDER", current: "mock" },
  { name: "TTS", env: "TTS_PROVIDER", current: "mock" },
  { name: "Storage", env: "STORAGE_PROVIDER", current: "local" },
];

export default function SettingsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Settings</h1>
      <div className={card}>
        <p className="mb-3 text-sm text-neutral-400">
          Providers are configured entirely through backend environment variables (<code>.env</code>) — there
          is no settings API yet, so this page is read-only reference, not a live configuration UI.
        </p>
        <table className="w-full text-sm">
          <thead className="text-left text-neutral-500">
            <tr>
              <th className="pb-2">Provider</th>
              <th className="pb-2">Env var</th>
              <th className="pb-2">Default</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-800">
            {PROVIDERS.map((p) => (
              <tr key={p.env}>
                <td className="py-1.5">{p.name}</td>
                <td className="py-1.5 font-mono text-neutral-400">{p.env}</td>
                <td className="py-1.5 text-neutral-400">{p.current}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className={card}>
        <p className="text-sm text-neutral-400">
          Real provider credentials, user accounts/auth, and per-channel settings are later-phase work
          (Phase 5 real providers, multi-channel support per spec section 62).
        </p>
      </div>
    </div>
  );
}
