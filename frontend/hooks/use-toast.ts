/**
 * Toast hook wrapper for Sonner
 * Provides a consistent API for toast notifications across the app
 */

import { toast as sonnerToast } from "sonner";

export type ToastVariant = "default" | "success" | "error" | "warning" | "info";

interface ToastOptions {
  title?: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
}

export function useToast() {
  const toast = ({
    title,
    description,
    variant = "default",
    duration,
  }: ToastOptions) => {
    const options = {
      duration: duration || 4000,
    };

    switch (variant) {
      case "success":
        return sonnerToast.success(title, {
          description,
          ...options,
        });
      case "error":
        return sonnerToast.error(title, {
          description,
          ...options,
        });
      case "warning":
        return sonnerToast.warning(title, {
          description,
          ...options,
        });
      case "info":
        return sonnerToast.info(title, {
          description,
          ...options,
        });
      default:
        return sonnerToast(title, {
          description,
          ...options,
        });
    }
  };

  return {
    toast,
    success: (title: string, description?: string) =>
      toast({ title, description, variant: "success" }),
    error: (title: string, description?: string) =>
      toast({ title, description, variant: "error" }),
    warning: (title: string, description?: string) =>
      toast({ title, description, variant: "warning" }),
    info: (title: string, description?: string) =>
      toast({ title, description, variant: "info" }),
  };
}
