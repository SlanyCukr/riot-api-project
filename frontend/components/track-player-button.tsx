"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Star, StarOff, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { trackPlayer, untrackPlayer, getTrackingStatus } from "@/lib/api";

interface TrackPlayerButtonProps {
  puuid: string;
  playerName?: string;
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm" | "lg" | "icon";
}

export function TrackPlayerButton({
  puuid,
  playerName,
  variant = "outline",
  size = "default",
}: TrackPlayerButtonProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Query for tracking status
  const { data: trackingStatus, isLoading: isLoadingStatus } = useQuery({
    queryKey: ["tracking-status", puuid],
    queryFn: async () => {
      const response = await getTrackingStatus(puuid);
      if (!response.success) {
        throw new Error(response.error.message);
      }
      return response.data;
    },
    retry: 1,
    staleTime: 30000, // 30 seconds
  });

  const isTracked = trackingStatus?.is_tracked ?? false;

  // Mutation for tracking
  const trackMutation = useMutation({
    mutationFn: async () => {
      const response = await trackPlayer(puuid);
      if (!response.success) {
        throw new Error(response.error.message);
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tracking-status", puuid] });
      toast({
        title: "Player tracked",
        description: `${playerName || "Player"} is now being tracked. New matches will be fetched automatically.`,
        variant: "success",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to track player",
        description: error.message,
        variant: "error",
      });
    },
  });

  // Mutation for untracking
  const untrackMutation = useMutation({
    mutationFn: async () => {
      const response = await untrackPlayer(puuid);
      if (!response.success) {
        throw new Error(response.error.message);
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tracking-status", puuid] });
      toast({
        title: "Player untracked",
        description: `${playerName || "Player"} is no longer being tracked.`,
        variant: "info",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to untrack player",
        description: error.message,
        variant: "error",
      });
    },
  });

  const handleToggleTracking = () => {
    if (isTracked) {
      untrackMutation.mutate();
    } else {
      trackMutation.mutate();
    }
  };

  const isLoading =
    isLoadingStatus || trackMutation.isPending || untrackMutation.isPending;

  return (
    <Button
      onClick={handleToggleTracking}
      disabled={isLoading}
      variant={isTracked ? "default" : variant}
      size={size}
      className="gap-2"
      aria-label={isTracked ? "Untrack player" : "Track player"}
    >
      {isLoading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : isTracked ? (
        <StarOff className="h-4 w-4" />
      ) : (
        <Star className="h-4 w-4" />
      )}
      {size !== "icon" && (isTracked ? "Tracked" : "Track")}
    </Button>
  );
}
