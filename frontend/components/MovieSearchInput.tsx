"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import type { MovieSearchResult } from "@/lib/types";

export default function MovieSearchInput({
  onSelect,
  placeholder = "Search for a movie...",
}: {
  onSelect: (result: MovieSearchResult) => void;
  placeholder?: string;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MovieSearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const trimmed = query.trim();

    const timeout = setTimeout(() => {
      if (trimmed.length < 2) {
        setResults([]);
        return;
      }

      setLoading(true);
      apiGet<MovieSearchResult[]>(`/api/movies/search?q=${encodeURIComponent(trimmed)}`)
        .then(setResults)
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, 300);

    return () => clearTimeout(timeout);
  }, [query]);

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-zinc-500 focus:border-white/30 focus:outline-none"
      />
      {loading && <p className="mt-1 text-xs text-zinc-500">Searching...</p>}
      {results.length > 0 && (
        <ul className="mt-2 max-h-64 divide-y divide-white/10 overflow-y-auto rounded-lg border border-white/10 bg-zinc-950">
          {results.map((result) => (
            <li key={result.tmdb_id}>
              <button
                type="button"
                onClick={() => {
                  onSelect(result);
                  setQuery("");
                  setResults([]);
                }}
                className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm text-white hover:bg-white/5"
              >
                {result.poster_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={result.poster_url} alt="" className="h-12 w-8 rounded object-cover" />
                ) : (
                  <div className="h-12 w-8 rounded bg-zinc-800" />
                )}
                <span>
                  {result.title}
                  {result.year ? ` (${result.year})` : ""}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
