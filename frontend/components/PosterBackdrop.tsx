interface Poster {
  title: string;
  poster_url: string;
}

const COLUMN_COUNT = 6;

function splitIntoColumns(posters: Poster[], columns: number): Poster[][] {
  const result: Poster[][] = Array.from({ length: columns }, () => []);
  posters.forEach((poster, index) => {
    result[index % columns].push(poster);
  });
  return result;
}

export default function PosterBackdrop({ posters }: { posters: Poster[] }) {
  if (posters.length < COLUMN_COUNT) {
    // Not enough posters for a convincing grid (e.g. TMDB key missing) — fail quietly.
    return null;
  }

  const columns = splitIntoColumns(posters, COLUMN_COUNT);

  return (
    <div aria-hidden className="animate-fade-in pointer-events-none absolute inset-0 overflow-hidden">
      <div className="flex h-full w-full gap-2 opacity-50">
        {columns.map((column, columnIndex) => (
          <div key={columnIndex} className="relative w-1/6 flex-none sm:w-auto sm:flex-1">
            <div
              className="animate-poster-scroll flex flex-col gap-2"
              style={{
                animationDuration: `${50 + columnIndex * 9}s`,
                animationDirection: columnIndex % 2 === 0 ? "normal" : "reverse",
              }}
            >
              {[...column, ...column].map((poster, posterIndex) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={`${poster.poster_url}-${posterIndex}`}
                  src={poster.poster_url}
                  alt=""
                  className="aspect-[2/3] w-full rounded-lg object-cover shadow-lg"
                />
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/75 to-black" />
    </div>
  );
}
