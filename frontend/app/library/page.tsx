"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AddLogModal from "@/components/AddLogModal";
import DiaryEntryTile from "@/components/DiaryEntryTile";
import EditDiaryEntryModal from "@/components/EditDiaryEntryModal";
import ImportLetterboxdModal from "@/components/ImportLetterboxdModal";
import { apiGet } from "@/lib/api";
import type { DiaryEntry } from "@/lib/types";
import { useCurrentUser } from "@/lib/useCurrentUser";

export default function LibraryPage() {
  const { user, loading } = useCurrentUser();
  const router = useRouter();
  const [entries, setEntries] = useState<DiaryEntry[] | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState<DiaryEntry | null>(null);

  function refetchEntries() {
    apiGet<DiaryEntry[]>("/api/library/diary").then(setEntries);
  }

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    refetchEntries();
  }, [user, loading, router]);

  if (loading || !user) {
    return null;
  }

  return (
    <div className="relative mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-white">Library</h1>
        <button
          onClick={() => setShowImportModal(true)}
          className="rounded-full border border-white/20 px-4 py-1.5 text-sm font-semibold text-white transition-transform hover:scale-105"
        >
          Import from Letterboxd
        </button>
      </div>

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

      {showImportModal && (
        <ImportLetterboxdModal onClose={() => setShowImportModal(false)} onImported={refetchEntries} />
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
