"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import MovieSearchInput from "@/components/MovieSearchInput";
import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import type { MovieListDetail, MovieSearchResult } from "@/lib/types";
import { useCurrentUser } from "@/lib/useCurrentUser";

export default function ListDetailPage({
  params,
}: {
  params: Promise<{ listId: string }>;
}) {
  const { listId } = use(params);
  const { user, loading } = useCurrentUser();
  const router = useRouter();
  const [list, setList] = useState<MovieListDetail | null>(null);
  const [showSearch, setShowSearch] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    apiGet<MovieListDetail>(`/api/library/lists/${listId}`).then(setList);
  }, [user, loading, router, listId]);

  async function handleAdd(result: MovieSearchResult) {
    const updated = await apiPost<MovieListDetail>(`/api/library/lists/${listId}/movies`, {
      tmdb_id: result.tmdb_id,
    });
    setList(updated);
    setShowSearch(false);
  }

  async function handleRemove(movieId: number) {
    await apiDelete(`/api/library/lists/${listId}/movies/${movieId}`);
    setList((current) =>
      current ? { ...current, items: current.items.filter((item) => item.movie.id !== movieId) } : current
    );
  }

  async function handleMove(index: number, direction: -1 | 1) {
    if (!list) return;
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= list.items.length) return;

    const reordered = [...list.items];
    [reordered[index], reordered[targetIndex]] = [reordered[targetIndex], reordered[index]];

    const updated = await apiPatch<MovieListDetail>(`/api/library/lists/${listId}/movies/reorder`, {
      movie_ids: reordered.map((item) => item.movie.id),
    });
    setList(updated);
  }

  if (loading || !user) {
    return null;
  }

  if (!list) {
    return <p className="p-6 text-sm text-zinc-500">Loading...</p>;
  }

  return (
    <div className="mx-auto w-full max-w-2xl flex-1 px-4 py-8">
      <h1 className="text-2xl font-semibold text-white">{list.name}</h1>
      {list.description && <p className="mt-1 text-sm text-zinc-400">{list.description}</p>}

      <div className="my-5">
        <button
          onClick={() => setShowSearch((value) => !value)}
          className="rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-zinc-900 transition-transform hover:scale-105"
        >
          {showSearch ? "Cancel" : "+ Add movie"}
        </button>
        {showSearch && (
          <div className="mt-3">
            <MovieSearchInput onSelect={handleAdd} />
          </div>
        )}
      </div>

      {list.items.length === 0 ? (
        <p className="text-sm text-zinc-500">No movies in this list yet.</p>
      ) : (
        <div className="space-y-3">
          {list.items.map((item, index) => (
            <div
              key={item.movie.id}
              className="flex items-center gap-4 rounded-xl border border-white/10 bg-white/5 p-3 transition-colors hover:bg-white/[0.07]"
            >
              <Link href={`/movie/${item.movie.tmdb_id}`} className="flex-none">
                {item.movie.poster_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={item.movie.poster_url} alt="" className="h-20 w-14 rounded-lg object-cover shadow-md" />
                ) : (
                  <div className="h-20 w-14 rounded-lg bg-zinc-800" />
                )}
              </Link>
              <div className="min-w-0 flex-1">
                <Link
                  href={`/movie/${item.movie.tmdb_id}`}
                  className="block truncate font-medium text-white hover:underline"
                >
                  {item.movie.title} {item.movie.year ? `(${item.movie.year})` : ""}
                </Link>
              </div>
              <div className="flex flex-none flex-col gap-1 text-xs text-zinc-400">
                <button onClick={() => handleMove(index, -1)} disabled={index === 0} className="hover:text-white disabled:opacity-30">
                  ▲
                </button>
                <button
                  onClick={() => handleMove(index, 1)}
                  disabled={index === list.items.length - 1}
                  className="hover:text-white disabled:opacity-30"
                >
                  ▼
                </button>
              </div>
              <button onClick={() => handleRemove(item.movie.id)} className="flex-none text-xs text-red-400 hover:text-red-300">
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
