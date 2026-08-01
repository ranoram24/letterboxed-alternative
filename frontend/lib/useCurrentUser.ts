"use client";

import { useEffect, useState } from "react";
import { ApiError, apiGet } from "./api";
import type { CurrentUser } from "./types";

export function useCurrentUser() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    apiGet<CurrentUser>("/api/auth/me")
      .then((data) => {
        if (!cancelled) setUser(data);
      })
      .catch((error) => {
        if (!cancelled) {
          if (error instanceof ApiError && error.status === 401) {
            setUser(null);
          } else {
            throw error;
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { user, loading };
}
