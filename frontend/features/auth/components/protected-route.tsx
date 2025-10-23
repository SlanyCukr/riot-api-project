"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../context/auth-context";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export function ProtectedRoute({
  children,
  requireAdmin = false,
}: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  // Immediate redirect on mount if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/sign-in");
    }
  }, [isLoading, isAuthenticated, router]);

  // Immediate redirect if admin required but user is not admin
  useEffect(() => {
    if (
      !isLoading &&
      isAuthenticated &&
      requireAdmin &&
      user &&
      !user.is_admin
    ) {
      router.replace("/");
    }
  }, [isLoading, isAuthenticated, requireAdmin, user, router]);

  // Immediate redirect if user is not active
  useEffect(() => {
    if (!isLoading && user && !user.is_active) {
      router.replace("/sign-in");
    }
  }, [isLoading, user, router]);

  // Don't render anything until auth check is complete
  if (isLoading) {
    return null;
  }

  // Don't render if not authenticated
  if (!isAuthenticated) {
    return null;
  }

  // Don't render if admin required but user is not admin
  if (requireAdmin && user && !user.is_admin) {
    return null;
  }

  // Don't render if user is not active
  if (user && !user.is_active) {
    return null;
  }

  // Render protected content
  return <>{children}</>;
}
