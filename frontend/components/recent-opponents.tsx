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
  // Fetch recent opponents with full player details (database only, no Riot API calls)
  const {
    data: opponentsResult,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["recent-opponents", puuid, limit],
    queryFn: () =>
      validatedGet(
        RecentOpponentsSchema,
        `/players/${puuid}/recent-opponents`,
        {
          limit,
        },
      ),
    enabled: !!puuid,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const players = opponentsResult?.success ? opponentsResult.data : [];

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

  if (!players || players.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Opponents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
            <UserSearch className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No recent opponents found in database
            </p>
            <p className="text-xs text-muted-foreground">
              Opponents will appear here after they&apos;ve been tracked or
              analyzed
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Recent Opponents</span>
          <Badge variant="secondary">{players.length} found</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
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
      </CardContent>
    </Card>
  );
}
