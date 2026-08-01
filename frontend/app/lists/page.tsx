"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ListCard from "@/components/ListCard";
import { apiGet, apiPost } from "@/lib/api";
import type { MovieList } from "@/lib/types";
import { useCurrentUser } from "@/lib/useCurrentUser";

export default function ListsPage() {
  const { user, loading } = useCurrentUser();
  const router = useRouter();
  const [lists, setLists] = useState<MovieList[] | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    apiGet<MovieList[]>("/api/library/lists").then(setLists);
  }, [user, loading, router]);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;

    setCreating(true);
    try {
      const list = await apiPost<MovieList>("/api/library/lists", {
        name,
        description: description || null,
      });
      setLists((current) => [list, ...(current ?? [])]);
      setName("");
      setDescription("");
    } finally {
      setCreating(false);
    }
  }

  if (loading || !user) {
    return null;
  }

  return (
    <div className="mx-auto w-full max-w-2xl flex-1 px-4 py-8">
      <h1 className="mb-5 text-2xl font-semibold text-white">Lists</h1>

      <form onSubmit={handleCreate} className="mb-6 space-y-2 rounded-xl border border-white/10 bg-white/5 p-4">
        <input
          type="text"
          placeholder="List name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-zinc-500 focus:border-white/30 focus:outline-none"
        />
        <input
          type="text"
          placeholder="Description (optional)"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-zinc-500 focus:border-white/30 focus:outline-none"
        />
        <button
          type="submit"
          disabled={creating}
          className="rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-zinc-900 transition-transform hover:scale-105 disabled:opacity-50"
        >
          {creating ? "Creating..." : "Create list"}
        </button>
      </form>

      {lists === null ? (
        <p className="text-sm text-zinc-500">Loading...</p>
      ) : lists.length === 0 ? (
        <p className="text-sm text-zinc-500">No lists yet.</p>
      ) : (
        <div className="space-y-3">
          {lists.map((list) => (
            <ListCard key={list.id} list={list} />
          ))}
        </div>
      )}
    </div>
  );
}
