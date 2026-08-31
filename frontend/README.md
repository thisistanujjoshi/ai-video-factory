AI Video Factory dashboard (Next.js App Router + TypeScript + Tailwind).

```bash
cp .env.local.example .env.local   # points at the backend, defaults to localhost:8000
npm install
npm run dev
```

Talks to the FastAPI backend in `../backend` over `NEXT_PUBLIC_API_URL` (see `lib/api.ts`). No server-side data fetching — every page is a client component that calls the backend directly, since this is an operator dashboard (mutations, live state), not a public site needing SSR/SEO.

Pages: `/dashboard`, `/content-profiles`, `/content-profiles/[id]`, `/ideas`, `/videos`, `/videos/[id]`, `/queue`, `/publishing` (placeholder — Phase 6), `/analytics` (placeholder — Phase 7), `/settings` (read-only provider reference).
