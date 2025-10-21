"use client";

import { Player, PlayerRankSchema } from "@/lib/schemas";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { User, Trophy } from "lucide-react";
import { TrackPlayerButton } from "@/components/track-player-button";
import { useQuery } from "@tanstack/react-query";
import { validatedGet } from "@/lib/api";

interface PlayerCardProps {
  player: Player;
}

// Helper function to get win rate colors based on percentage
function getWinRateColors(winRate: number): string {
  if (winRate >= 60) {
    // Excellent (60%+) - Bright lime/chartreuse (distinct from emerald backgrounds)
    return "text-lime-700 dark:text-lime-300 font-semibold";
  } else if (winRate >= 55) {
    // Good (55-60%) - Bright green (strong contrast)
    return "text-green-700 dark:text-green-300 font-medium";
  } else if (winRate >= 50) {
    // Above average (50-55%) - Teal (distinct from rank colors)
    return "text-teal-700 dark:text-teal-300";
  } else if (winRate >= 45) {
    // Average (45-50%) - Yellow/amber (strong contrast)
    return "text-amber-700 dark:text-amber-300";
  } else if (winRate >= 40) {
    // Below average (40-45%) - Orange (strong contrast)
    return "text-orange-700 dark:text-orange-300";
  } else {
    // Poor (<40%) - Red (strong contrast)
    return "text-red-700 dark:text-red-300 font-medium";
  }
}

// Helper function to get rank colors based on tier
function getRankColors(tier: string): {
  gradient: string;
  icon: string;
  text: string;
  badge: string;
} {
  const normalizedTier = tier.toUpperCase();

  switch (normalizedTier) {
    case "IRON":
      return {
        gradient: "from-gray-400/10 to-gray-500/10",
        icon: "text-gray-500 dark:text-gray-400",
        text: "text-gray-700 dark:text-gray-300",
        badge: "bg-gray-500/20 text-gray-700 dark:text-gray-300",
      };
    case "BRONZE":
      return {
        gradient: "from-orange-700/10 to-orange-800/10",
        icon: "text-orange-700 dark:text-orange-600",
        text: "text-orange-800 dark:text-orange-400",
        badge: "bg-orange-700/20 text-orange-800 dark:text-orange-400",
      };
    case "SILVER":
      return {
        gradient: "from-slate-400/10 to-slate-500/10",
        icon: "text-slate-500 dark:text-slate-400",
        text: "text-slate-700 dark:text-slate-300",
        badge: "bg-slate-500/20 text-slate-700 dark:text-slate-300",
      };
    case "GOLD":
      return {
        gradient: "from-yellow-500/10 to-amber-500/10",
        icon: "text-yellow-600 dark:text-yellow-500",
        text: "text-yellow-700 dark:text-yellow-400",
        badge: "bg-yellow-600/20 text-yellow-700 dark:text-yellow-400",
      };
    case "PLATINUM":
      return {
        gradient: "from-cyan-500/10 to-teal-500/10",
        icon: "text-cyan-600 dark:text-cyan-500",
        text: "text-cyan-700 dark:text-cyan-400",
        badge: "bg-cyan-600/20 text-cyan-700 dark:text-cyan-400",
      };
    case "EMERALD":
      return {
        gradient: "from-emerald-500/10 to-green-500/10",
        icon: "text-emerald-600 dark:text-emerald-500",
        text: "text-emerald-700 dark:text-emerald-400",
        badge: "bg-emerald-600/20 text-emerald-700 dark:text-emerald-400",
      };
    case "DIAMOND":
      return {
        gradient: "from-blue-500/10 to-indigo-500/10",
        icon: "text-blue-600 dark:text-blue-500",
        text: "text-blue-700 dark:text-blue-400",
        badge: "bg-blue-600/20 text-blue-700 dark:text-blue-400",
      };
    case "MASTER":
      return {
        gradient: "from-purple-500/10 to-fuchsia-500/10",
        icon: "text-purple-600 dark:text-purple-500",
        text: "text-purple-700 dark:text-purple-400",
        badge: "bg-purple-600/20 text-purple-700 dark:text-purple-400",
      };
    case "GRANDMASTER":
      return {
        gradient: "from-red-500/10 to-rose-500/10",
        icon: "text-red-600 dark:text-red-500",
        text: "text-red-700 dark:text-red-400",
        badge: "bg-red-600/20 text-red-700 dark:text-red-400",
      };
    case "CHALLENGER":
      return {
        gradient: "from-yellow-400/20 to-orange-500/20 via-red-500/20",
        icon: "text-yellow-500 dark:text-yellow-400",
        text: "text-transparent bg-clip-text bg-gradient-to-r from-yellow-500 via-red-500 to-orange-500",
        badge:
          "bg-gradient-to-r from-yellow-500/20 via-red-500/20 to-orange-500/20 text-yellow-600 dark:text-yellow-400 font-bold",
      };
    default:
      return {
        gradient: "from-gray-500/10 to-gray-600/10",
        icon: "text-gray-600 dark:text-gray-500",
        text: "text-gray-700 dark:text-gray-400",
        badge: "bg-gray-600/20 text-gray-700 dark:text-gray-400",
      };
  }
}

export function PlayerCard({ player }: PlayerCardProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  // Fetch player rank
  const { data: rank } = useQuery({
    queryKey: ["player-rank", player.puuid],
    queryFn: async () => {
      const result = await validatedGet(
        PlayerRankSchema.nullable(),
        `/players/${player.puuid}/rank`,
      );
      if (!result.success) {
        return null;
      }
      return result.data;
    },
    retry: false,
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center space-x-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            {/* TODO [SPY-61]: Use actual player's icon, and until we have them, use some league icon as a placeholder */}
            <User className="h-6 w-6 text-primary" />
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-xl">
                  {player.riot_id && player.tag_line
                    ? `${player.riot_id}#${player.tag_line}`
                    : player.summoner_name}
                </CardTitle>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>{player.platform.toUpperCase()}</span>
                  <Badge variant="secondary">
                    Level {player.account_level}
                  </Badge>
                  {player.is_tracked && (
                    <Badge variant="default" className="bg-yellow-600">
                      Tracked
                    </Badge>
                  )}
                </div>
              </div>
              <TrackPlayerButton
                puuid={player.puuid}
                playerName={
                  player.riot_id && player.tag_line
                    ? `${player.riot_id}#${player.tag_line}`
                    : player.summoner_name
                }
                variant="outline"
                size="default"
              />
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Rank Display */}
          {rank &&
            (() => {
              const colors = getRankColors(rank.tier);
              return (
                <div
                  className={`rounded-lg border bg-gradient-to-br ${colors.gradient} p-4`}
                >
                  <div className="flex items-center gap-3">
                    <Trophy className={`h-8 w-8 ${colors.icon}`} />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-lg font-bold ${colors.text}`}>
                          {rank.display_rank}
                        </span>
                        <Badge className={`font-mono ${colors.badge} border-0`}>
                          {rank.league_points} LP
                        </Badge>
                      </div>
                      <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
                        <span>
                          {rank.wins}W / {rank.losses}L
                        </span>
                        <span>•</span>
                        <span className={getWinRateColors(rank.win_rate)}>
                          {rank.win_rate.toFixed(1)}% WR
                        </span>
                        {rank.hot_streak && (
                          <>
                            <span>•</span>
                            <Badge variant="destructive" className="text-xs">
                              🔥 Hot Streak
                            </Badge>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-medium text-muted-foreground">PUUID</p>
              <p className="font-mono text-xs">
                {player.puuid.slice(0, 20)}...
              </p>
            </div>
            <div>
              <p className="font-medium text-muted-foreground">Last Seen</p>
              <p>{formatDate(player.last_seen)}</p>
            </div>
            <div>
              <p className="font-medium text-muted-foreground">
                Account Tracked Since
              </p>
              <p>{formatDate(player.created_at)}</p>
            </div>
            <div>
              <p className="font-medium text-muted-foreground">Platform</p>
              <p className="uppercase">{player.platform}</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
