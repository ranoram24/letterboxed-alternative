"use client";

import { useState } from "react";
import { apiDelete, apiPatch } from "@/lib/api";
import type { DiaryEntry } from "@/lib/types";

const inputClass =
  "mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-zinc-500 focus:border-white/30 focus:outline-none";

export default function EditDiaryEntryModal({
  entry,
  onClose,
  onUpdated,
  onDeleted,
}: {
  entry: DiaryEntry;
  onClose: () => void;
  onUpdated: (entry: DiaryEntry) => void;
  onDeleted: (entryId: number) => void;
}) {
  const [watchedDate, setWatchedDate] = useState(entry.watched_date);
  const [rating, setRating] = useState(entry.rating?.toString() ?? "");
  const [rewatch, setRewatch] = useState(entry.rewatch);
  const [reviewText, setReviewText] = useState(entry.review_text ?? "");
  const [tags, setTags] = useState(entry.tags.join(", "));
  const [liked, setLiked] = useState(entry.liked);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const updated = await apiPatch<DiaryEntry>(`/api/library/diary/${entry.id}`, {
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
      onUpdated(updated);
      onClose();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await apiDelete(`/api/library/diary/${entry.id}`);
      onDeleted(entry.id);
      onClose();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 backdrop-blur-sm sm:items-center">
      <div className="max-h-[90dvh] w-full max-w-md overflow-y-auto rounded-t-2xl border border-white/10 bg-zinc-950 p-5 shadow-2xl sm:rounded-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Edit watch</h2>
          <button onClick={onClose} className="text-sm text-zinc-500 hover:text-white">
            Close
          </button>
        </div>

        <div className="mb-4 flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-2.5">
          {entry.movie.poster_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={entry.movie.poster_url} alt="" className="h-16 w-11 rounded-md object-cover" />
          ) : (
            <div className="h-16 w-11 rounded-md bg-zinc-800" />
          )}
          <p className="font-medium text-white">
            {entry.movie.title} {entry.movie.year ? `(${entry.movie.year})` : ""}
          </p>
        </div>

        <form onSubmit={handleSave} className="space-y-4">
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

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 rounded-lg bg-white px-3 py-2.5 text-sm font-semibold text-zinc-900 transition-transform hover:scale-[1.02] disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="rounded-lg border border-red-500/40 px-4 py-2.5 text-sm font-semibold text-red-400 hover:bg-red-500/10 disabled:opacity-50"
            >
              {deleting ? "..." : "Delete"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
