"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getAccessToken } from "@/lib/session";

interface UseAuthGuardResult {
  isCheckingAuth: boolean;
  isAuthenticated: boolean;
}

export function useAuthGuard(): UseAuthGuardResult {
  const router = useRouter();
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const token = getAccessToken();

    if (!token) {
      setIsAuthenticated(false);
      setIsCheckingAuth(false);
      router.replace("/login");
      return;
    }

    setIsAuthenticated(true);
    setIsCheckingAuth(false);
  }, [router]);

  return {
    isCheckingAuth,
    isAuthenticated,
  };
}