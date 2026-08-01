"use client";

import Link from "next/link";
import { apiDelete } from "@/lib/api";
import type { WatchlistItem } from "@/lib/types";

export default function WatchlistTile({
  item,
  onRemoved,
}: {
  item: WatchlistItem;
  onRemoved: (movieId: number) => void;
}) {
  async function handleRemove() {
    await apiDelete(`/api/library/watchlist/${item.movie.id}`);
    onRemoved(item.movie.id);
  }

  return (
    <div className="group relative">
      <Link
        href={`/movie/${item.movie.tmdb_id}`}
        className="block overflow-hidden rounded-lg shadow-lg transition-transform duration-200 group-hover:scale-105"
      >
        {item.movie.poster_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={item.movie.poster_url} alt={item.movie.title} className="aspect-[2/3] w-full object-cover" />
        ) : (
          <div className="flex aspect-[2/3] w-full items-center justify-center bg-zinc-800 p-2">
            <span className="text-center text-xs text-zinc-400">{item.movie.title}</span>
          </div>
        )}
      </Link>
      <button
        onClick={handleRemove}
        aria-label="Remove from watchlist"
        className="absolute top-1.5 right-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-black/70 text-sm leading-none text-white opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-500/90 focus:opacity-100"
      >
        ×
      </button>
    </div>
  );
}
