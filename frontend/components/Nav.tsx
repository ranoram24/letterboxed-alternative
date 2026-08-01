"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCurrentUser } from "@/lib/useCurrentUser";
import UserMenu from "./UserMenu";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/library", label: "Library" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/lists", label: "Lists" },
];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export default function Nav() {
  const { user } = useCurrentUser();
  const pathname = usePathname();

  if (pathname === "/login" || !user) {
    return null;
  }

  return (
    <nav className="sticky top-0 z-40 flex items-center justify-between gap-4 border-b border-white/10 bg-black/60 px-4 py-3 backdrop-blur-md sm:px-6">
      <div className="flex min-w-0 items-center gap-3 sm:gap-6">
        <span className="hidden font-semibold tracking-tight text-white sm:inline">Movie Explorer</span>
        <div className="no-scrollbar flex gap-1 overflow-x-auto text-sm">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={
                isActive(pathname, link.href)
                  ? "rounded-full bg-white/10 px-3 py-1.5 font-medium text-white"
                  : "rounded-full px-3 py-1.5 text-zinc-400 hover:text-white"
              }
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
      <UserMenu user={user} />
    </nav>
  );
}
