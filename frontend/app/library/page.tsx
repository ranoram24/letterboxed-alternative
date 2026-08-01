"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AddLogModal from "@/components/AddLogModal";
import DiaryEntryTile from "@/components/DiaryEntryTile";
import EditDiaryEntryModal from "@/components/EditDiaryEntryModal";
import { apiGet } from "@/lib/api";
import type { DiaryEntry } from "@/lib/types";
import { useCurrentUser } from "@/lib/useCurrentUser";

export default function LibraryPage() {
  const { user, loading } = useCurrentUser();
  const router = useRouter();
  const [entries, setEntries] = useState<DiaryEntry[] | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState<DiaryEntry | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    apiGet<DiaryEntry[]>("/api/library/diary").then(setEntries);
  }, [user, loading, router]);

  if (loading || !user) {
    return null;
  }

  return (
    <div className="relative mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
      <h1 className="mb-5 text-2xl font-semibold text-white">Library</h1>

      {entries === null ? (
        <p className="text-sm text-zinc-500">Loading...</p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-zinc-500">
          No watches logged yet. Tap the + button to log your first movie.
        </p>
      ) : (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6">
          {entries.map((entry) => (
            <DiaryEntryTile key={entry.id} entry={entry} onClick={() => setEditingEntry(entry)} />
          ))}
        </div>
      )}

      <button
        onClick={() => setShowAddModal(true)}
        aria-label="Log a watch"
        className="fixed right-6 bottom-6 flex h-14 w-14 items-center justify-center rounded-full bg-white text-2xl font-light text-zinc-900 shadow-[0_8px_30px_rgba(0,0,0,0.5)] transition-transform hover:scale-105"
      >
        +
      </button>

      {showAddModal && (
        <AddLogModal
          onClose={() => setShowAddModal(false)}
          onLogged={(entry) => {
            setEntries((current) => [entry, ...(current ?? [])]);
            setShowAddModal(false);
          }}
        />
      )}

      {editingEntry && (
        <EditDiaryEntryModal
          entry={editingEntry}
          onClose={() => setEditingEntry(null)}
          onUpdated={(updated) =>
            setEntries((current) => (current ?? []).map((item) => (item.id === updated.id ? updated : item)))
          }
          onDeleted={(entryId) =>
            setEntries((current) => (current ?? []).filter((item) => item.id !== entryId))
          }
        />
      )}
    </div>
  );
}
