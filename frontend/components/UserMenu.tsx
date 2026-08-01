"use client";

import { useRouter } from "next/navigation";
import { apiPost } from "@/lib/api";
import type { CurrentUser } from "@/lib/types";

export default function UserMenu({ user }: { user: CurrentUser }) {
  const router = useRouter();

  async function handleSignOut() {
    await apiPost("/api/auth/logout");
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="flex items-center gap-3">
      {user.profile_picture_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={user.profile_picture_url}
          alt={user.display_name}
          referrerPolicy="no-referrer"
          className="h-8 w-8 rounded-full ring-2 ring-white/20"
        />
      ) : (
        <div className="h-8 w-8 rounded-full bg-zinc-700 ring-2 ring-white/20" />
      )}
      <span className="hidden text-sm font-medium text-white sm:inline">{user.display_name}</span>
      <button onClick={handleSignOut} className="text-sm text-zinc-400 hover:text-white">
        Sign out
      </button>
    </div>
  );
}
