import GoogleIcon from "@/components/GoogleIcon";
import PosterBackdrop from "@/components/PosterBackdrop";
import { API_BASE_URL } from "@/lib/api";
import type { MovieSearchResult } from "@/lib/types";

async function fetchPopularPosters(): Promise<{ title: string; poster_url: string }[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/movies/popular`, {
      // Revalidate hourly so the backdrop stays fresh without hitting TMDb on every login.
      next: { revalidate: 3600 },
    });
    if (!response.ok) return [];
    const movies = (await response.json()) as MovieSearchResult[];
    return movies
      .filter((movie): movie is MovieSearchResult & { poster_url: string } => movie.poster_url !== null)
      .map((movie) => ({ title: movie.title, poster_url: movie.poster_url }));
  } catch {
    return [];
  }
}

export default async function LoginPage() {
  const posters = await fetchPopularPosters();

  return (
    <div className="relative isolate flex min-h-[100dvh] flex-1 flex-col items-center justify-center overflow-hidden bg-black px-4 text-center">
      <PosterBackdrop posters={posters} />

      <div className="relative z-10 flex flex-col items-center gap-4">
        <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
          Movie Explorer
        </h1>
        <p className="max-w-sm text-base text-zinc-300">
          Track, rate, and review the movies you watch — sign in to get started.
        </p>

        {/* Real full-page navigation (not a fetch) — required so the browser follows
            the Google OAuth redirect chain and the session cookie set on callback sticks. */}
        <a
          href={`${API_BASE_URL}/api/auth/login/google`}
          className="mt-2 flex items-center gap-3 rounded-full bg-white px-6 py-3 text-sm font-medium text-zinc-900 shadow-[0_8px_30px_rgba(0,0,0,0.5)] transition-transform hover:scale-105 hover:shadow-[0_8px_40px_rgba(255,255,255,0.25)]"
        >
          <GoogleIcon />
          Sign in with Google
        </a>
      </div>
    </div>
  );
}
