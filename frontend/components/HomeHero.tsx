import Link from "next/link";
import type { Movie } from "@/lib/types";

export default function HomeHero({ movie }: { movie: Movie }) {
  return (
    <div className="relative -mx-4 mb-10 h-[340px] overflow-hidden sm:-mx-6 sm:h-[420px] sm:rounded-2xl">
      {movie.backdrop_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={movie.backdrop_url} alt="" className="h-full w-full object-cover" />
      ) : (
        <div className="h-full w-full bg-zinc-900" />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black via-black/50 to-transparent" />
      <div className="absolute inset-x-0 bottom-0 p-6 sm:p-8">
        <p className="mb-1 text-xs font-semibold tracking-wide text-amber-400 uppercase">Trending Now</p>
        <h2 className="max-w-lg text-2xl font-bold text-white sm:text-4xl">{movie.title}</h2>
        {movie.tagline && <p className="mt-1 max-w-md text-sm text-zinc-300 italic">{movie.tagline}</p>}
        <Link
          href={`/movie/${movie.tmdb_id}`}
          className="mt-4 inline-block rounded-full bg-white px-5 py-2 text-sm font-semibold text-zinc-900 transition-transform hover:scale-105"
        >
          View Details
        </Link>
      </div>
    </div>
  );
}
