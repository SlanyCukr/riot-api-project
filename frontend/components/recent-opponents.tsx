"use client";

import { useQuery } from "@tanstack/react-query";
import { validatedGet } from "@/lib/api";
import { RecentOpponentsSchema, PlayerSchema, Player } from "@/lib/schemas";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, UserSearch, AlertCircle } from "lucide-react";

interface RecentOpponentsProps {
  puuid: string;
  limit?: number;
  onAnalyzePlayer?: (player: Player) => void;
}

export function RecentOpponents({
  puuid,
  limit = 10,
  onAnalyzePlayer,
}: RecentOpponentsProps) {
  // Fetch recent opponent PUUIDs
  const {
    data: opponentsResult,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["recent-opponents", puuid, limit],
    queryFn: () =>
      validatedGet(RecentOpponentsSchema, `/players/${puuid}/recent`, {
        limit,
      }),
    enabled: !!puuid,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch player details for each opponent PUUID
  const opponentPuuids = opponentsResult?.success ? opponentsResult.data : [];

  const {
    data: playersData,
    isLoading: isLoadingPlayers,
    error: playersError,
  } = useQuery({
    queryKey: ["opponent-players", opponentPuuids],
    queryFn: async () => {
      // Fetch all player details in parallel
      const results = await Promise.all(
        opponentPuuids.map((opponentPuuid) =>
          validatedGet(PlayerSchema, `/players/${opponentPuuid}`),
        ),
      );
      return results
        .filter((result) => result.success)
        .map((result) => (result.success ? result.data : null))
        .filter((player): player is Player => player !== null);
    },
    enabled: opponentPuuids.length > 0,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Opponents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || (opponentsResult && !opponentsResult.success)) {
    const errorMessage = opponentsResult?.success
      ? "Unknown error"
      : opponentsResult?.error.message || "Failed to load recent opponents";

    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Opponents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="text-sm text-muted-foreground">{errorMessage}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!opponentPuuids || opponentPuuids.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Opponents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
            <UserSearch className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No recent opponents found
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const players = playersData || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Recent Opponents</span>
          <Badge variant="secondary">{opponentPuuids.length} found</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoadingPlayers ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : playersError ? (
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="text-sm text-muted-foreground">
              Failed to load player details
            </p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {players.map((player) => (
              <Card
                key={player.puuid}
                className="transition-shadow hover:shadow-md"
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate font-semibold">
                          {player.riot_id || player.summoner_name}
                        </p>
                        {player.is_tracked && (
                          <Badge variant="outline" className="text-xs">
                            Tracked
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {player.platform.toUpperCase()}
                      </p>
                      {player.account_level && (
                        <p className="text-xs text-muted-foreground">
                          Level {player.account_level}
                        </p>
                      )}
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onAnalyzePlayer?.(player)}
                      className="shrink-0"
                    >
                      <UserSearch className="mr-1 h-4 w-4" />
                      Analyze
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
