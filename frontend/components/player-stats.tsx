"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Trophy,
  Swords,
  Skull,
  Heart,
  Target,
  Eye,
  BarChart3,
  Activity,
} from "lucide-react";

import {
  MatchStatsResponseSchema,
  type MatchStatsResponse,
} from "@/lib/schemas";
import { validatedGet } from "@/lib/api";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";

interface PlayerStatsProps {
  puuid: string;
  queueFilter?: number;
  limit?: number;
}

export function PlayerStats({
  puuid,
  queueFilter = 420,
  limit = 50,
}: PlayerStatsProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["player-stats", puuid, queueFilter, limit],
    queryFn: async () => {
      const result = await validatedGet(
        MatchStatsResponseSchema,
        `/matches/player/${puuid}/stats`,
        { queue: queueFilter, limit }
      );

      if (!result.success) {
        throw new Error(result.error.message);
      }

      return result.data;
    },
    enabled: !!puuid,
  });

  if (isLoading) {
    return <PlayerStatsSkeleton />;
  }

  if (error) {
    return (
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">
            Failed to Load Stats
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {error instanceof Error
              ? error.message
              : "Unable to fetch player statistics"}
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.total_matches === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary" />
            Player Statistics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No statistics available yet. Stats will appear once matches are
            fetched.
          </p>
        </CardContent>
      </Card>
    );
  }

  return <PlayerStatsDisplay stats={data} />;
}

function PlayerStatsDisplay({ stats }: { stats: MatchStatsResponse }) {
  const winRatePercent = stats.win_rate * 100;

  const getKDAColor = (kda: number) => {
    if (kda >= 4.0) return "bg-emerald-500 text-white";
    if (kda >= 3.0) return "bg-green-500 text-white";
    if (kda >= 2.0) return "bg-yellow-500 text-white";
    return "bg-red-500 text-white";
  };

  const getWinRateColor = (winRate: number) => {
    if (winRate >= 60) return "text-emerald-600 dark:text-emerald-400";
    if (winRate >= 50) return "text-green-600 dark:text-green-400";
    if (winRate >= 45) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary" />
            Player Statistics
          </CardTitle>
          <Badge variant="secondary">
            Based on last{" "}
            {stats.total_matches === 1
              ? "match"
              : stats.total_matches + " matches"}
          </Badge>
        </div>
        {stats.total_matches < 20 && (
          <p className="mt-2 text-xs text-muted-foreground">
            Statistics will be more accurate with more matches
          </p>
        )}
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Win Rate Section */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Trophy className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Win Rate</span>
              </div>
              <span
                className={`text-2xl font-bold ${getWinRateColor(
                  winRatePercent
                )}`}
              >
                {winRatePercent.toFixed(1)}%
              </span>
            </div>
            <Progress value={winRatePercent} className="h-2" />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{stats.wins}W</span>
              <span>{stats.losses}L</span>
            </div>
          </div>

          {/* KDA Section */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Average KDA</span>
              </div>
              <Badge className={getKDAColor(stats.avg_kda)}>
                {stats.avg_kda.toFixed(2)}
              </Badge>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <StatBox
                icon={<Swords className="h-4 w-4" />}
                label="Kills"
                value={stats.avg_kills.toFixed(1)}
                color="text-blue-600 dark:text-blue-400"
              />
              <StatBox
                icon={<Skull className="h-4 w-4" />}
                label="Deaths"
                value={stats.avg_deaths.toFixed(1)}
                color="text-red-600 dark:text-red-400"
              />
              <StatBox
                icon={<Heart className="h-4 w-4" />}
                label="Assists"
                value={stats.avg_assists.toFixed(1)}
                color="text-green-600 dark:text-green-400"
              />
            </div>
          </div>

          {/* Additional Stats */}
          <div className="grid grid-cols-2 gap-4">
            <StatBox
              icon={<Target className="h-4 w-4" />}
              label="Avg CS"
              value={stats.avg_cs.toFixed(1)}
              color="text-purple-600 dark:text-purple-400"
            />
            <StatBox
              icon={<Eye className="h-4 w-4" />}
              label="Avg Vision"
              value={stats.avg_vision_score.toFixed(1)}
              color="text-orange-600 dark:text-orange-400"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface StatBoxProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  color?: string;
}

function StatBox({
  icon,
  label,
  value,
  color = "text-foreground",
}: StatBoxProps) {
  return (
    <div className="flex flex-col items-center rounded-lg border bg-muted/50 p-3">
      <div className="mb-1 flex items-center gap-1 text-muted-foreground">
        {icon}
      </div>
      <div className={`text-xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

function PlayerStatsSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-5 w-20" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-16" />
            </div>
            <Skeleton className="h-2 w-full" />
            <div className="flex justify-between">
              <Skeleton className="h-3 w-12" />
              <Skeleton className="h-3 w-12" />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-6 w-16" />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
