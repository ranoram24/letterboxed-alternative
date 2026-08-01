import Link from "next/link";
import type { MovieList } from "@/lib/types";

export default function ListCard({ list }: { list: MovieList }) {
  return (
    <Link
      href={`/lists/${list.id}`}
      className="block rounded-xl border border-white/10 bg-white/5 p-4 transition-colors hover:bg-white/[0.07]"
    >
      <p className="font-medium text-white">{list.name}</p>
      {list.description && <p className="mt-0.5 text-sm text-zinc-400">{list.description}</p>}
    </Link>
  );
}
