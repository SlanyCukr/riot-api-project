"use client";

import { useQuery } from "@tanstack/react-query";
import { TrendingUp, Users } from "lucide-react";

import { getLatestMatchmakingAnalysis } from "@/lib/core/api";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface MatchmakingAnalysisResultsProps {
  puuid: string;
}

export function MatchmakingAnalysisResults({
  puuid,
}: MatchmakingAnalysisResultsProps) {
  // Use a separate query key to avoid conflicts with MatchmakingAnalysis component
  const {
    data: latestAnalysis,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["matchmaking-analysis-results", puuid],
    queryFn: async () => {
      const result = await getLatestMatchmakingAnalysis(puuid);
      if (!result.success) {
        if (result.error.status === 404) {
          return null;
        }
        throw new Error(result.error.message);
      }
      return result.data;
    },
    retry: false,
    staleTime: 30000, // Keep results fresh for 30 seconds
  });

  // Simple rule: Show if there's any analysis with results in DB
  // Same logic as button text: {latestAnalysis ? "Run New Analysis" : "Start Analysis"}
  // Don't show while loading or if no data
  if (isLoading || error || !latestAnalysis) {
    return null;
  }

  // Don't show if there are no results (nothing to display)
  if (!latestAnalysis.results) {
    return null;
  }

  const { team_avg_winrate, enemy_avg_winrate, matches_analyzed } =
    latestAnalysis.results;

  // Calculate the difference to show if matchmaking was fair
  const winrateDiff = team_avg_winrate - enemy_avg_winrate;
  const isFavorable = winrateDiff > 0.05; // >5% difference in your favor
  const isUnfavorable = winrateDiff < -0.05; // >5% difference against you
  const isFair = !isFavorable && !isUnfavorable;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          Recent Analysis Results
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Team</TableHead>
              <TableHead className="text-right">
                Average Winrate (Last 10 Matches)
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell className="font-medium">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Your Team
                </div>
              </TableCell>
              <TableCell className="text-right font-mono">
                <span
                  className={
                    isFavorable
                      ? "text-green-600 dark:text-green-400"
                      : isUnfavorable
                        ? "text-red-600 dark:text-red-400"
                        : ""
                  }
                >
                  {(team_avg_winrate * 100).toFixed(1)}%
                </span>
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="font-medium">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Enemy Team
                </div>
              </TableCell>
              <TableCell className="text-right font-mono">
                <span
                  className={
                    isUnfavorable
                      ? "text-green-600 dark:text-green-400"
                      : isFavorable
                        ? "text-red-600 dark:text-red-400"
                        : ""
                  }
                >
                  {(enemy_avg_winrate * 100).toFixed(1)}%
                </span>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>

        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            Based on {matches_analyzed} ranked matches
          </p>

          {isFavorable && (
            <p className="text-sm text-green-600 dark:text-green-400">
              ✓ Your teammates had higher average winrates than enemies
            </p>
          )}
          {isUnfavorable && (
            <p className="text-sm text-red-600 dark:text-red-400">
              ✗ Your enemies had higher average winrates than teammates
            </p>
          )}
          {isFair && (
            <p className="text-sm text-muted-foreground">
              ≈ Matchmaking appears balanced (winrates within 5%)
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
