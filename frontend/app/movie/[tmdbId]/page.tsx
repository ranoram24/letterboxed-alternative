"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AddLogModal from "@/components/AddLogModal";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import type { Movie, MovieReview, MovieSearchResult, WatchlistItem } from "@/lib/types";
import { useCurrentUser } from "@/lib/useCurrentUser";

export default function MovieDetailPage({
  params,
}: {
  params: Promise<{ tmdbId: string }>;
}) {
  const { tmdbId } = use(params);
  const { user, loading } = useCurrentUser();
  const router = useRouter();

  const [movie, setMovie] = useState<Movie | null>(null);
  const [reviews, setReviews] = useState<MovieReview[] | null>(null);
  const [watchlistItem, setWatchlistItem] = useState<WatchlistItem | null>(null);
  const [watchlistBusy, setWatchlistBusy] = useState(false);
  const [showLogModal, setShowLogModal] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }

    apiGet<Movie>(`/api/movies/${tmdbId}`).then(setMovie);
    apiGet<MovieReview[]>(`/api/movies/${tmdbId}/reviews`).then(setReviews);
    apiGet<WatchlistItem[]>("/api/library/watchlist").then((items) => {
      setWatchlistItem(items.find((item) => item.movie.tmdb_id === Number(tmdbId)) ?? null);
    });
  }, [user, loading, router, tmdbId]);

  async function handleToggleWatchlist() {
    if (!movie) return;
    setWatchlistBusy(true);
    try {
      if (watchlistItem) {
        await apiDelete(`/api/library/watchlist/${movie.id}`);
        setWatchlistItem(null);
      } else {
        const item = await apiPost<WatchlistItem>("/api/library/watchlist", { tmdb_id: movie.tmdb_id });
        setWatchlistItem(item);
      }
    } finally {
      setWatchlistBusy(false);
    }
  }

  if (loading || !user || !movie) {
    return null;
  }

  const movieAsSearchResult: MovieSearchResult = {
    tmdb_id: movie.tmdb_id,
    title: movie.title,
    year: movie.year,
    poster_url: movie.poster_url,
  };

  return (
    <div className="relative flex-1">
      {movie.backdrop_url && (
        <div className="absolute inset-x-0 top-0 h-[420px] overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={movie.backdrop_url} alt="" className="h-full w-full object-cover opacity-30" />
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-black/60 to-black" />
        </div>
      )}

      <div className="relative mx-auto w-full max-w-4xl px-4 pt-6 pb-16 sm:px-6">
        <button onClick={() => router.back()} className="mb-6 text-sm text-zinc-400 hover:text-white">
          ← Back
        </button>

        <div className="flex flex-col gap-8 sm:flex-row">
          <div className="mx-auto w-48 flex-none sm:mx-0">
            {movie.poster_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={movie.poster_url} alt="" className="aspect-[2/3] w-full rounded-xl object-cover shadow-2xl" />
            ) : (
              <div className="aspect-[2/3] w-full rounded-xl bg-zinc-800" />
            )}

            <div className="mt-4 flex flex-col gap-2">
              <button
                onClick={() => setShowLogModal(true)}
                className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-zinc-900 transition-transform hover:scale-105"
              >
                Log
              </button>
              <button
                onClick={handleToggleWatchlist}
                disabled={watchlistBusy}
                className={
                  watchlistItem
                    ? "rounded-full bg-red-500/90 px-4 py-2 text-sm font-semibold text-white transition-transform hover:scale-105 disabled:opacity-50"
                    : "rounded-full border border-white/20 px-4 py-2 text-sm font-semibold text-white transition-transform hover:scale-105 disabled:opacity-50"
                }
              >
                {watchlistItem ? "Remove from Watchlist" : "+ Watchlist"}
              </button>
            </div>

            {movie.vote_average !== null && (
              <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3 text-center">
                <p className="text-2xl font-semibold text-amber-400">★ {(movie.vote_average / 2).toFixed(1)}</p>
                <p className="text-xs text-zinc-500">
                  {movie.vote_count?.toLocaleString()} TMDb rating{movie.vote_count === 1 ? "" : "s"}
                </p>
              </div>
            )}
          </div>

          <div className="min-w-0 flex-1">
            <h1 className="text-3xl font-bold text-white sm:text-4xl">{movie.title}</h1>
            <p className="mt-1 text-sm text-zinc-400">
              {movie.year}
              {movie.directors.length > 0 && <> · Directed by {movie.directors.join(", ")}</>}
              {movie.runtime && <> · {movie.runtime} min</>}
            </p>

            {movie.tagline && <p className="mt-4 text-sm tracking-wide text-zinc-400 uppercase">{movie.tagline}</p>}

            {movie.overview && <p className="mt-3 leading-relaxed text-zinc-200">{movie.overview}</p>}

            {movie.cast_members.length > 0 && (
              <div className="mt-8">
                <h2 className="mb-3 text-sm font-semibold tracking-wide text-zinc-400 uppercase">Cast</h2>
                <div className="flex flex-wrap gap-2">
                  {movie.cast_members.map((name) => (
                    <span key={name} className="rounded-full bg-white/10 px-3 py-1 text-sm text-zinc-200">
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-10">
              <h2 className="mb-3 text-sm font-semibold tracking-wide text-zinc-400 uppercase">
                Reviews from Movie Explorer members
              </h2>
              {reviews === null ? (
                <p className="text-sm text-zinc-500">Loading reviews...</p>
              ) : reviews.length === 0 ? (
                <p className="text-sm text-zinc-500">No reviews yet — be the first to log this movie.</p>
              ) : (
                <div className="space-y-4">
                  {reviews.map((review, index) => (
                    <div key={index} className="rounded-xl border border-white/10 bg-white/5 p-4">
                      <div className="mb-2 flex items-center gap-2">
                        {review.reviewer_picture_url ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={review.reviewer_picture_url}
                            alt=""
                            referrerPolicy="no-referrer"
                            className="h-7 w-7 rounded-full"
                          />
                        ) : (
                          <div className="h-7 w-7 rounded-full bg-zinc-700" />
                        )}
                        <span className="text-sm font-medium text-white">{review.reviewer_name}</span>
                        {review.rating !== null && (
                          <span className="text-xs text-amber-400">★ {review.rating}</span>
                        )}
                        {review.liked && <span className="text-xs text-red-400">♥</span>}
                      </div>
                      <p className="text-sm text-zinc-300">{review.review_text}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {showLogModal && (
        <AddLogModal
          initialMovie={movieAsSearchResult}
          closeLabel="Back"
          onClose={() => setShowLogModal(false)}
          onLogged={() => setShowLogModal(false)}
        />
      )}
    </div>
  );
}
