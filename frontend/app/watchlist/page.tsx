"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import MovieSearchInput from "@/components/MovieSearchInput";
import WatchlistTile from "@/components/WatchlistTile";
import { apiGet, apiPost } from "@/lib/api";
import type { MovieSearchResult, WatchlistItem as WatchlistItemType } from "@/lib/types";
import { useCurrentUser } from "@/lib/useCurrentUser";

export default function WatchlistPage() {
  const { user, loading } = useCurrentUser();
  const router = useRouter();
  const [items, setItems] = useState<WatchlistItemType[] | null>(null);
  const [showSearch, setShowSearch] = useState(false);

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

  if (loading || !user) {
    return null;
  }

  return (
    <div className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
      <div className="mb-5 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">Watchlist</h1>
        <button
          onClick={() => setShowSearch((value) => !value)}
          className="rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-zinc-900 transition-transform hover:scale-105"
        >
          {showSearch ? "Cancel" : "+ Add"}
        </button>
      </div>

      {showSearch && (
        <div className="mb-6">
          <MovieSearchInput onSelect={handleAdd} />
        </div>
      )}

      {items === null ? (
        <p className="text-sm text-zinc-500">Loading...</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-zinc-500">Your watchlist is empty.</p>
      ) : (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6">
          {items.map((item) => (
            <WatchlistTile
              key={item.id}
              item={item}
              onRemoved={(movieId) =>
                setItems((current) => (current ?? []).filter((existing) => existing.movie.id !== movieId))
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
