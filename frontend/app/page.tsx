"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import HomeHero from "@/components/HomeHero";
import PosterRow from "@/components/PosterRow";
import { apiGet } from "@/lib/api";
import type { Movie, MovieSearchResult, RecommendedMovie } from "@/lib/types";
import { useCurrentUser } from "@/lib/useCurrentUser";

function RecommendedRowSkeleton() {
  return (
    <section>
      <h2 className="mb-3 text-lg font-semibold text-white">Recommended for You</h2>
      <div className="flex gap-3 overflow-x-hidden pb-2">
        {Array.from({ length: 6 }).map((_, index) => (
          <div
            key={index}
            className="aspect-[2/3] w-28 flex-none animate-pulse rounded-lg bg-white/5 sm:w-32"
          />
        ))}
      </div>
    </section>
  );
}

export default function HomePage() {
  const { user, loading } = useCurrentUser();
  const router = useRouter();

  const [popular, setPopular] = useState<MovieSearchResult[]>([]);
  const [nowPlaying, setNowPlaying] = useState<MovieSearchResult[]>([]);
  const [recommended, setRecommended] = useState<RecommendedMovie[]>([]);
  const [recommendedLoading, setRecommendedLoading] = useState(true);
  const [featured, setFeatured] = useState<Movie | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }

    apiGet<MovieSearchResult[]>("/api/movies/popular").then((movies) => {
      setPopular(movies);
      const topPick = movies[0];
      if (topPick) {
        apiGet<Movie>(`/api/movies/${topPick.tmdb_id}`).then(setFeatured);
      }
    });

    apiGet<MovieSearchResult[]>("/api/movies/now-playing").then(setNowPlaying);

    // Runs independently of the rows above so a slow AI call never holds up the rest of
    // the page — this row just shows a skeleton, then fills in (or disappears entirely
    // for brand-new users with no taste signal yet) once it resolves.
    apiGet<RecommendedMovie[]>("/api/movies/recommendations")
      .then(setRecommended)
      .finally(() => setRecommendedLoading(false));
  }, [user, loading, router]);

  if (loading || !user) {
    return null;
  }

  const recommendedMovies = recommended.map((item) => item.movie);
  const recommendedReasons = new Map(recommended.map((item) => [item.movie.tmdb_id, item.reason]));

  return (
    <div className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
      {featured && <HomeHero movie={featured} />}

      <h1 className="mb-1 text-2xl font-semibold text-white">
        Welcome back, {user.display_name.split(" ")[0]}
      </h1>
      <p className="mb-8 text-sm text-zinc-400">Here&apos;s what&apos;s worth watching.</p>

      <div className="space-y-10">
        <PosterRow title="Popular Right Now" movies={popular} />

        <PosterRow title="New Releases" movies={nowPlaying} />

        {recommendedLoading ? (
          <RecommendedRowSkeleton />
        ) : (
          recommendedMovies.length > 0 && (
            <PosterRow title="Recommended for You" movies={recommendedMovies} reasons={recommendedReasons} />
          )
        )}
      </div>
    </div>
  );
}
