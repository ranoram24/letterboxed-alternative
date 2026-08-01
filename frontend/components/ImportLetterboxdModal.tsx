"use client";

import { useEffect, useRef, useState } from "react";
import AddLogModal from "@/components/AddLogModal";
import { apiGet, apiUploadWithProgress, ApiError } from "@/lib/api";
import type { ImportJob, UnmatchedFilm } from "@/lib/types";

type Phase = "idle" | "uploading" | "processing" | "completed" | "failed";

const POLL_INTERVAL_MS = 2000;

export default function ImportLetterboxdModal({
  onClose,
  onImported,
}: {
  onClose: () => void;
  onImported: () => void;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [uploadPercent, setUploadPercent] = useState(0);
  const [job, setJob] = useState<ImportJob | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [addingFilm, setAddingFilm] = useState<UnmatchedFilm | null>(null);
  const [addedTitles, setAddedTitles] = useState<Set<string>>(new Set());
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (phase !== "processing" || !job) return;

    const interval = setInterval(async () => {
      try {
        const updated = await apiGet<ImportJob>(`/api/import/letterboxd/${job.id}`);
        setJob(updated);
        if (updated.status === "completed") {
          setPhase("completed");
          onImported();
        } else if (updated.status === "failed") {
          setErrorMessage(updated.error_message ?? "The import failed unexpectedly.");
          setPhase("failed");
        }
      } catch {
        setErrorMessage("Lost connection while checking import progress.");
        setPhase("failed");
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [phase, job, onImported]);

  async function handleFileChosen(file: File) {
    setErrorMessage(null);
    setPhase("uploading");
    setUploadPercent(0);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const created = await apiUploadWithProgress<ImportJob>(
        "/api/import/letterboxd",
        formData,
        setUploadPercent
      );
      setJob(created);
      setPhase("processing");
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError && error.status === 400
          ? error.message
          : "Couldn't upload that file — try again."
      );
      setPhase("failed");
    }
  }

  function handleReset() {
    setPhase("idle");
    setJob(null);
    setErrorMessage(null);
    setUploadPercent(0);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  const summary = job?.summary ?? null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 backdrop-blur-sm sm:items-center">
      <div className="max-h-[90dvh] w-full max-w-lg overflow-y-auto rounded-t-2xl border border-white/10 bg-zinc-950 p-5 shadow-2xl sm:rounded-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Import from Letterboxd</h2>
          <button onClick={onClose} className="text-sm text-zinc-500 hover:text-white">
            Close
          </button>
        </div>

        {phase === "idle" && (
          <div className="space-y-3">
            <p className="text-sm text-zinc-400">
              Upload the zip Letterboxd gives you from{" "}
              <span className="text-zinc-300">Settings → Data → Export</span>. We&apos;ll pull in your
              diary, ratings, reviews, watchlist, and lists.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) handleFileChosen(file);
              }}
              className="block w-full text-sm text-zinc-300 file:mr-3 file:rounded-full file:border-0 file:bg-white file:px-4 file:py-1.5 file:text-sm file:font-semibold file:text-zinc-900"
            />
          </div>
        )}

        {phase === "uploading" && (
          <div className="space-y-3">
            <p className="text-sm text-zinc-300">Uploading... {uploadPercent}%</p>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-white transition-all"
                style={{ width: `${uploadPercent}%` }}
              />
            </div>
          </div>
        )}

        {phase === "processing" && (
          <div className="space-y-3">
            <p className="text-sm text-zinc-300">
              Matching your movies against TMDb
              {job?.total_films ? ` (${job.processed_films} of ${job.total_films})` : "..."}
            </p>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-white transition-all"
                style={{
                  width: job?.total_films ? `${(job.processed_films / job.total_films) * 100}%` : "5%",
                }}
              />
            </div>
            <p className="text-xs text-zinc-500">This can take a few minutes for a large library — feel free to leave this open.</p>
          </div>
        )}

        {phase === "failed" && (
          <div className="space-y-3">
            <p className="text-sm text-red-400">{errorMessage}</p>
            <button
              onClick={handleReset}
              className="rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-zinc-900"
            >
              Try again
            </button>
          </div>
        )}

        {phase === "completed" && summary && (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <SummaryStat label="Diary entries" value={summary.diary_entries_imported} skipped={summary.diary_entries_skipped} />
              <SummaryStat label="Watchlist items" value={summary.watchlist_items_imported} skipped={summary.watchlist_items_skipped} />
              <SummaryStat label="Lists" value={summary.lists_imported} />
              <SummaryStat label="Movies added to lists" value={summary.list_movies_imported} />
            </div>

            {summary.unmatched_films.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-semibold text-zinc-300">
                  Couldn&apos;t confidently match {summary.unmatched_films.length} film
                  {summary.unmatched_films.length === 1 ? "" : "s"}
                </h3>
                <ul className="space-y-1.5">
                  {summary.unmatched_films.map((film) => {
                    const key = `${film.title}-${film.year ?? ""}`;
                    const added = addedTitles.has(key);
                    return (
                      <li
                        key={key}
                        className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm"
                      >
                        <span className="text-zinc-300">
                          {film.title} {film.year ? `(${film.year})` : ""}
                        </span>
                        <button
                          onClick={() => setAddingFilm(film)}
                          disabled={added}
                          className="text-xs font-semibold text-white hover:underline disabled:text-zinc-500 disabled:no-underline"
                        >
                          {added ? "Added" : "Add manually"}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            <button onClick={onClose} className="rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-zinc-900">
              Done
            </button>
          </div>
        )}
      </div>

      {addingFilm && (
        <AddLogModal
          initialQuery={addingFilm.title}
          closeLabel="Back"
          onClose={() => setAddingFilm(null)}
          onLogged={() => {
            setAddedTitles((current) => new Set(current).add(`${addingFilm.title}-${addingFilm.year ?? ""}`));
            setAddingFilm(null);
            onImported();
          }}
        />
      )}
    </div>
  );
}

function SummaryStat({ label, value, skipped }: { label: string; value: number; skipped?: number }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-3">
      <p className="text-2xl font-semibold text-white">{value}</p>
      <p className="text-xs text-zinc-400">{label}</p>
      {skipped ? <p className="mt-0.5 text-[11px] text-zinc-500">{skipped} already in your library</p> : null}
    </div>
  );
}
