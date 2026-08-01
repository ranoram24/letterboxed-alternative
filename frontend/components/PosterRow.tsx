import Link from "next/link";
import type { MovieSearchResult } from "@/lib/types";

export default function PosterRow({
  title,
  movies,
  badge,
}: {
  title: string;
  movies: MovieSearchResult[];
  badge?: (movie: MovieSearchResult) => string | null;
}) {
  if (movies.length === 0) return null;

  return (
    <section>
      <h2 className="mb-3 text-lg font-semibold text-white">{title}</h2>
      <div className="no-scrollbar flex gap-3 overflow-x-auto pb-2">
        {movies.map((movie) => (
          <Link
            key={movie.tmdb_id}
            href={`/movie/${movie.tmdb_id}`}
            className="group w-28 flex-none overflow-hidden rounded-lg shadow-lg transition-transform duration-200 hover:scale-105 sm:w-32"
          >
            <div className="relative">
              {movie.poster_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={movie.poster_url} alt={movie.title} className="aspect-[2/3] w-full object-cover" />
              ) : (
                <div className="flex aspect-[2/3] w-full items-center justify-center bg-zinc-800 p-2">
                  <span className="text-center text-xs text-zinc-400">{movie.title}</span>
                </div>
              )}
              {badge?.(movie) && (
                <span className="absolute top-1.5 right-1.5 rounded-full bg-black/70 px-1.5 py-0.5 text-[10px] font-medium text-white">
                  {badge(movie)}
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
