import type { DiaryEntry } from "@/lib/types";

export default function DiaryEntryTile({
  entry,
  onClick,
}: {
  entry: DiaryEntry;
  onClick: () => void;
}) {
  return (
    <button onClick={onClick} className="group block w-full text-left">
      <div className="relative overflow-hidden rounded-lg shadow-lg transition-transform duration-200 group-hover:scale-105">
        {entry.movie.poster_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={entry.movie.poster_url} alt={entry.movie.title} className="aspect-[2/3] w-full object-cover" />
        ) : (
          <div className="flex aspect-[2/3] w-full items-center justify-center bg-zinc-800 p-2">
            <span className="text-center text-xs text-zinc-400">{entry.movie.title}</span>
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
        {entry.rating !== null && (
          <span className="absolute bottom-1.5 left-1.5 rounded-full bg-black/70 px-1.5 py-0.5 text-[10px] font-medium text-amber-400">
            ★ {entry.rating}
          </span>
        )}
        {entry.liked && (
          <span className="absolute top-1.5 right-1.5 text-sm text-red-400 drop-shadow">♥</span>
        )}
      </div>
    </button>
  );
}
