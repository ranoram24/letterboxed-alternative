"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import HomeHero from "@/components/HomeHero";
import PosterRow from "@/components/PosterRow";
import { apiGet } from "@/lib/api";
import type { DiaryEntry, Movie, MovieSearchResult } from "@/lib/types";
import { useCurrentUser } from "@/lib/useCurrentUser";

function diaryEntryToMovie(entry: DiaryEntry): MovieSearchResult {
  return {
    tmdb_id: entry.movie.tmdb_id,
    title: entry.movie.title,
    year: entry.movie.year,
    poster_url: entry.movie.poster_url,
  };
}

export default function HomePage() {
  const { user, loading } = useCurrentUser();
  const router = useRouter();

  const [recentEntries, setRecentEntries] = useState<DiaryEntry[]>([]);
  const [popular, setPopular] = useState<MovieSearchResult[]>([]);
  const [nowPlaying, setNowPlaying] = useState<MovieSearchResult[]>([]);
  const [featured, setFeatured] = useState<Movie | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }

    apiGet<DiaryEntry[]>("/api/library/diary").then((entries) => {
      // Entries arrive most-recently-watched first; keep only each movie's most recent
      // entry so a rewatch doesn't show the same poster twice in this row.
      const seenTmdbIds = new Set<number>();
      const deduped = entries.filter((entry) => {
        if (seenTmdbIds.has(entry.movie.tmdb_id)) return false;
        seenTmdbIds.add(entry.movie.tmdb_id);
        return true;
      });
      setRecentEntries(deduped.slice(0, 10));
    });

    apiGet<MovieSearchResult[]>("/api/movies/popular").then((movies) => {
      setPopular(movies);
      const topPick = movies[0];
      if (topPick) {
        apiGet<Movie>(`/api/movies/${topPick.tmdb_id}`).then(setFeatured);
      }
    });

    apiGet<MovieSearchResult[]>("/api/movies/now-playing").then(setNowPlaying);
  }, [user, loading, router]);

  if (loading || !user) {
    return null;
  }

  const recentAsMovies = recentEntries.map(diaryEntryToMovie);
  const ratingByTmdbId = new Map(recentEntries.map((entry) => [entry.movie.tmdb_id, entry.rating]));

  return (
    <div className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
      {featured && <HomeHero movie={featured} />}

      <h1 className="mb-1 text-2xl font-semibold text-white">
        Welcome back, {user.display_name.split(" ")[0]}
      </h1>
      <p className="mb-8 text-sm text-zinc-400">Here&apos;s what&apos;s worth watching.</p>

      <div className="space-y-10">
        <PosterRow
          title="Recently Watched"
          movies={recentAsMovies}
          badge={(movie) => {
            const rating = ratingByTmdbId.get(movie.tmdb_id);
            return rating ? `★ ${rating}` : null;
          }}
        />

        <PosterRow title="Popular Right Now" movies={popular} />

        <PosterRow title="New Releases" movies={nowPlaying} />
      </div>
    </div>
  );
}
