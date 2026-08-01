"use client";

import { useState } from "react";
import { apiPost } from "@/lib/api";
import type { DiaryEntry, MovieSearchResult } from "@/lib/types";
import MovieSearchInput from "./MovieSearchInput";

const inputClass =
  "mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-zinc-500 focus:border-white/30 focus:outline-none";

export default function AddLogModal({
  initialMovie = null,
  initialQuery = "",
  closeLabel = "Close",
  onClose,
  onLogged,
}: {
  initialMovie?: MovieSearchResult | null;
  initialQuery?: string;
  closeLabel?: string;
  onClose: () => void;
  onLogged: (entry: DiaryEntry) => void;
}) {
  const [selected, setSelected] = useState<MovieSearchResult | null>(initialMovie);
  const [watchedDate, setWatchedDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [rating, setRating] = useState("");
  const [rewatch, setRewatch] = useState(false);
  const [reviewText, setReviewText] = useState("");
  const [tags, setTags] = useState("");
  const [liked, setLiked] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!selected) return;

    setSubmitting(true);
    setError(null);
    try {
      const entry = await apiPost<DiaryEntry>("/api/library/diary", {
        tmdb_id: selected.tmdb_id,
        watched_date: watchedDate,
        rating: rating ? Number(rating) : null,
        rewatch,
        review_text: reviewText || null,
        tags: tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
        liked,
      });
      onLogged(entry);
    } catch {
      setError("Couldn't log this watch. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 backdrop-blur-sm sm:items-center">
      <div className="max-h-[90dvh] w-full max-w-md overflow-y-auto rounded-t-2xl border border-white/10 bg-zinc-950 p-5 shadow-2xl sm:rounded-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Log a watch</h2>
          <button onClick={onClose} className="text-sm text-zinc-500 hover:text-white">
            {closeLabel}
          </button>
        </div>

        {!selected ? (
          <MovieSearchInput onSelect={setSelected} initialQuery={initialQuery} />
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-2.5">
              {selected.poster_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={selected.poster_url} alt="" className="h-16 w-11 rounded-md object-cover" />
              ) : (
                <div className="h-16 w-11 rounded-md bg-zinc-800" />
              )}
              <div className="flex-1">
                <p className="font-medium text-white">
                  {selected.title} {selected.year ? `(${selected.year})` : ""}
                </p>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  className="text-xs text-zinc-500 hover:text-white"
                >
                  Change movie
                </button>
              </div>
            </div>

            <label className="block text-sm text-zinc-300">
              Watched date
              <input
                type="date"
                required
                value={watchedDate}
                onChange={(event) => setWatchedDate(event.target.value)}
                className={inputClass}
              />
            </label>

            <label className="block text-sm text-zinc-300">
              Rating (0.5 - 5.0)
              <input
                type="number"
                min={0.5}
                max={5}
                step={0.5}
                value={rating}
                onChange={(event) => setRating(event.target.value)}
                className={inputClass}
              />
            </label>

            <label className="block text-sm text-zinc-300">
              Review
              <textarea
                value={reviewText}
                onChange={(event) => setReviewText(event.target.value)}
                rows={3}
                className={inputClass}
              />
            </label>

            <label className="block text-sm text-zinc-300">
              Tags (comma separated)
              <input
                type="text"
                value={tags}
                onChange={(event) => setTags(event.target.value)}
                className={inputClass}
              />
            </label>

            <div className="flex gap-4 text-sm text-zinc-300">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={rewatch} onChange={(event) => setRewatch(event.target.checked)} />
                Rewatch
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={liked} onChange={(event) => setLiked(event.target.checked)} />
                Liked
              </label>
            </div>

            {error && <p className="text-sm text-red-400">{error}</p>}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-white px-3 py-2.5 text-sm font-semibold text-zinc-900 transition-transform hover:scale-[1.02] disabled:opacity-50"
            >
              {submitting ? "Logging..." : "Log watch"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
