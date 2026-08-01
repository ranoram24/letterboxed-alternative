"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import MovieSearchInput from "@/components/MovieSearchInput";
import WatchlistTile from "@/components/WatchlistTile";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import type { MovieSearchResult, WatchlistItem as WatchlistItemType, WhatToChooseResult } from "@/lib/types";
import { useCurrentUser } from "@/lib/useCurrentUser";

function buildLocalTimeContext() {
  const now = new Date();
  // Shift by the timezone offset so formatting as ISO yields the *local* wall-clock
  // time rather than UTC — the server only needs the hour, not a true UTC instant.
  const localDatetime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 19);
  return { local_datetime: localDatetime, timezone_offset_minutes: now.getTimezoneOffset() };
}

export default function WatchlistPage() {
  const { user, loading } = useCurrentUser();
  const router = useRouter();
  const [items, setItems] = useState<WatchlistItemType[] | null>(null);
  const [showSearch, setShowSearch] = useState(false);

  const [pick, setPick] = useState<WhatToChooseResult | null>(null);
  const [pickLoading, setPickLoading] = useState(false);
  const [pickError, setPickError] = useState<string | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    apiGet<WatchlistItemType[]>("/api/library/watchlist").then(setItems);
  }, [user, loading, router]);

  async function handleAdd(result: MovieSearchResult) {
    const item = await apiPost<WatchlistItemType>("/api/library/watchlist", {
      tmdb_id: result.tmdb_id,
    });
    setItems((current) => {
      const withoutDuplicate = (current ?? []).filter((existing) => existing.id !== item.id);
      return [item, ...withoutDuplicate];
    });
    setShowSearch(false);
  }

  async function handleWhatToChoose() {
    setPickLoading(true);
    setPickError(null);
    try {
      const result = await apiPost<WhatToChooseResult>(
        "/api/library/watchlist/what-to-choose",
        buildLocalTimeContext()
      );
      setPick(result);
    } catch (error) {
      setPickError(
        error instanceof ApiError && error.status === 400
          ? "Add something to your watchlist first."
          : "Couldn't get a pick right now — try again in a moment."
      );
    } finally {
      setPickLoading(false);
    }
  }

  function handleItemRemoved(movieId: number) {
    setItems((current) => (current ?? []).filter((existing) => existing.movie.id !== movieId));
    setPick((current) => (current?.movie.id === movieId ? null : current));
  }

  if (loading || !user) {
    return null;
  }

  const isEmpty = items !== null && items.length === 0;

  return (
    <div className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-white">Watchlist</h1>
        <div className="flex gap-2">
          <button
            onClick={handleWhatToChoose}
            disabled={isEmpty || pickLoading}
            className="rounded-full border border-white/20 px-4 py-1.5 text-sm font-semibold text-white transition-transform hover:scale-105 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:scale-100"
          >
            {pickLoading ? "Thinking..." : "What to Choose"}
          </button>
          <button
            onClick={() => setShowSearch((value) => !value)}
            className="rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-zinc-900 transition-transform hover:scale-105"
          >
            {showSearch ? "Cancel" : "+ Add"}
          </button>
        </div>
      </div>

      {pickError && <p className="mb-4 text-sm text-red-400">{pickError}</p>}

      {pick && (
        <div className="mb-6 flex gap-4 rounded-xl border border-amber-400/40 bg-amber-400/5 p-4">
          <Link href={`/movie/${pick.movie.tmdb_id}`} className="flex-none">
            {pick.movie.poster_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={pick.movie.poster_url}
                alt={pick.movie.title}
                className="h-24 w-16 rounded-lg object-cover shadow-md"
              />
            ) : (
              <div className="h-24 w-16 rounded-lg bg-zinc-800" />
            )}
          </Link>
          <div className="min-w-0">
            <p className="text-xs font-semibold tracking-wide text-amber-400 uppercase">Your Pick</p>
            <Link href={`/movie/${pick.movie.tmdb_id}`} className="font-medium text-white hover:underline">
              {pick.movie.title} {pick.movie.year ? `(${pick.movie.year})` : ""}
            </Link>
            <p className="mt-1 text-sm text-zinc-300">{pick.reason}</p>
          </div>
          <button
            onClick={() => setPick(null)}
            aria-label="Dismiss pick"
            className="ml-auto flex-none text-sm text-zinc-500 hover:text-white"
          >
            ×
          </button>
        </div>
      )}

      {showSearch && (
        <div className="mb-6">
          <MovieSearchInput onSelect={handleAdd} />
        </div>
      )}

      {items === null ? (
        <p className="text-sm text-zinc-500">Loading...</p>
      ) : isEmpty ? (
        <p className="text-sm text-zinc-500">Your watchlist is empty.</p>
      ) : (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6">
          {items.map((item) => (
            <WatchlistTile
              key={item.id}
              item={item}
              highlighted={pick?.movie.id === item.movie.id}
              onRemoved={handleItemRemoved}
            />
          ))}
        </div>
      )}
    </div>
  );
}
