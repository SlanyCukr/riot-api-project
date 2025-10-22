"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { validatedGet } from "@/lib/core/api";
import { PlayerSchema, type Player } from "@/lib/core/schemas";
import { z } from "zod";
import { api } from "@/lib/core/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Users, Loader2, UserMinus, Eye } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

const TrackedPlayersSchema = z.array(PlayerSchema);

interface TrackedPlayersListProps {
  onViewPlayer?: (player: Player) => void;
}

export function TrackedPlayersList({ onViewPlayer }: TrackedPlayersListProps) {
  const queryClient = useQueryClient();
  const router = useRouter();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["tracked-players"],
    queryFn: async () => {
      const result = await validatedGet(
        TrackedPlayersSchema,
        "/players/tracked/list",
      );

      if (!result.success) {
        throw new Error(result.error.message);
      }

      return result.data;
    },
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  const untrackMutation = useMutation({
    mutationFn: async (puuid: string) => {
      const response = await api.delete(`/players/${puuid}/track`);
      return response.data;
    },
    onSuccess: (_, puuid) => {
      // Invalidate and refetch tracked players
      queryClient.invalidateQueries({ queryKey: ["tracked-players"] });

      // Find player name for toast
      const player = data?.find((p) => p.puuid === puuid);
      toast.success(
        `Successfully removed ${
          player?.summoner_name || "player"
        } from tracked players`,
      );
    },
    onError: (error: Error) => {
      toast.error(`Failed to untrack player: ${error.message}`);
    },
  });

  const handleUntrack = (player: Player) => {
    if (
      window.confirm(
        `Are you sure you want to stop tracking ${player.summoner_name}?`,
      )
    ) {
      untrackMutation.mutate(player.puuid);
    }
  };

  const handleViewPlayer = (player: Player) => {
    if (onViewPlayer) {
      onViewPlayer(player);
    } else {
      // Navigate to player analysis page with the player
      router.push(`/player-analysis?puuid=${player.puuid}`);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Users className="h-5 w-5 text-primary" />
            <CardTitle>Tracked Players</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Users className="h-5 w-5 text-primary" />
            <CardTitle>Tracked Players</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-center">
            <p className="text-sm text-destructive">
              Failed to load tracked players. Please try again.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={() => refetch()}
            >
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Users className="h-5 w-5 text-primary" />
              <CardTitle>Tracked Players</CardTitle>
            </div>
            <Badge variant="secondary">0 Players</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-dashed p-8 text-center">
            <Users className="mx-auto h-12 w-12 text-muted-foreground/50" />
            <p className="mt-4 text-sm text-muted-foreground">
              No tracked players yet. Add a player above to start tracking.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Users className="h-5 w-5 text-primary" />
            <CardTitle>Tracked Players</CardTitle>
          </div>
          <Badge variant="secondary">{data.length} Players</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {data.map((player) => (
            <div
              key={player.puuid}
              className="flex items-center justify-between rounded-lg border bg-card p-4 transition-colors hover:bg-accent/50"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">{player.summoner_name}</h3>
                  {player.riot_id && player.tag_line && (
                    <span className="text-sm text-muted-foreground">
                      #{player.tag_line}
                    </span>
                  )}
                </div>
                <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="uppercase">{player.platform}</span>
                  {player.account_level && (
                    <span>Level {player.account_level}</span>
                  )}
                  <span>
                    Last seen: {new Date(player.last_seen).toLocaleDateString()}
                  </span>
                </div>
              </div>
              {/* TODO [SPY-67]: Add button for redirect to the Matchmaking Analysis page */}
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleViewPlayer(player)}
                >
                  <Eye className="mr-1 h-4 w-4" />
                  View
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleUntrack(player)}
                  disabled={untrackMutation.isPending}
                >
                  {untrackMutation.isPending &&
                  untrackMutation.variables === player.puuid ? (
                    <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                  ) : (
                    <UserMinus className="mr-1 h-4 w-4" />
                  )}
                  Untrack
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
