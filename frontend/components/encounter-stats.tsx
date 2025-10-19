"use client";

import { useQuery } from "@tanstack/react-query";
import {
  EncounterStatsResponseSchema,
  type EncounterData,
} from "@/lib/schemas";
import { validatedGet } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Users, TrendingUp, AlertTriangle, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface EncounterStatsProps {
  puuid: string;
  onAnalyzePlayer?: (encounterPuuid: string) => void;
}

export function EncounterStats({
  puuid,
  onAnalyzePlayer,
}: EncounterStatsProps) {
  const {
    data: encounterStats,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["encounter-stats", puuid],
    queryFn: async () => {
      const result = await validatedGet(
        EncounterStatsResponseSchema,
        `/matches/player/${puuid}/encounter-stats`,
        { limit: 50, min_encounters: 3 }
      );
      if (!result.success) {
        throw new Error(result.error.message);
      }
      return result.data;
    },
    retry: 1,
  });

  const getSuspicionIndicator = (
    data: EncounterData
  ): { level: "high" | "medium" | "low"; message: string } | null => {
    const totalGames = data.total_encounters;
    const teammateRate = data.as_teammate / totalGames;
    const winRate = data.teammate_win_rate;

    // High suspicion: Many games together with high win rate
    if (
      totalGames >= 5 &&
      teammateRate >= 0.7 &&
      winRate >= 0.75 &&
      data.as_teammate >= 5
    ) {
      return {
        level: "high",
        message: `${(winRate * 100).toFixed(
          0
        )}% win rate together - possible duo abuse`,
      };
    }

    // Medium suspicion: Several games together with good win rate
    if (totalGames >= 4 && teammateRate >= 0.6 && winRate >= 0.65) {
      return {
        level: "medium",
        message: `${(winRate * 100).toFixed(0)}% win rate in ${
          data.as_teammate
        } games together`,
      };
    }

    // Low suspicion: Notable pattern but not extreme
    if (totalGames >= 3 && winRate >= 0.8) {
      return {
        level: "low",
        message: `High win rate (${(winRate * 100).toFixed(
          0
        )}%) when playing together`,
      };
    }

    return null;
  };

  const getSuspicionColor = (level: "high" | "medium" | "low"): string => {
    switch (level) {
      case "high":
        return "text-red-600 bg-red-50 border-red-200";
      case "medium":
        return "text-orange-600 bg-orange-50 border-orange-200";
      case "low":
        return "text-yellow-600 bg-yellow-50 border-yellow-200";
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Encounter Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Encounter Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {error instanceof Error
                ? error.message
                : "Failed to load encounter statistics"}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!encounterStats || encounterStats.total_unique_encounters === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-blue-600" />
            Encounter Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertDescription>
              No frequent encounters found. Play more matches to see patterns.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  // Sort encounters by total games (most frequent first)
  const sortedEncounters = Object.entries(encounterStats.encounters).sort(
    ([, a], [, b]) => b.total_encounters - a.total_encounters
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5 text-blue-600" />
          Encounter Analysis
        </CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          Players frequently encountered in {encounterStats.matches_analyzed}{" "}
          recent matches
        </p>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Player</TableHead>
                <TableHead className="text-center">Total Games</TableHead>
                <TableHead className="text-center">As Teammate</TableHead>
                <TableHead className="text-center">As Opponent</TableHead>
                <TableHead className="text-center">Teammate Win Rate</TableHead>
                <TableHead className="text-center">Avg KDA</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedEncounters.map(([encounterPuuid, data]) => {
                const suspicion = getSuspicionIndicator(data);
                const mostRecentMatch =
                  data.recent_matches[data.recent_matches.length - 1];

                return (
                  <TableRow
                    key={encounterPuuid}
                    className={cn(
                      suspicion && suspicion.level === "high" && "bg-red-50/50"
                    )}
                  >
                    <TableCell>
                      <div>
                        <div className="font-medium">
                          {mostRecentMatch?.summoner_name || "Unknown"}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {encounterPuuid.slice(0, 8)}...
                        </div>
                        {suspicion && (
                          <div className="mt-1">
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-xs",
                                getSuspicionColor(suspicion.level)
                              )}
                            >
                              {suspicion.level === "high" && "⚠️ "}
                              {suspicion.message}
                            </Badge>
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-center font-medium">
                      {data.total_encounters}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant="secondary">{data.as_teammate}</Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant="outline">{data.as_opponent}</Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <div
                        className={cn(
                          "font-medium",
                          data.teammate_win_rate >= 0.75
                            ? "text-red-600"
                            : data.teammate_win_rate >= 0.6
                            ? "text-orange-600"
                            : data.teammate_win_rate >= 0.5
                            ? "text-green-600"
                            : "text-muted-foreground"
                        )}
                      >
                        {data.as_teammate > 0
                          ? `${(data.teammate_win_rate * 100).toFixed(0)}%`
                          : "N/A"}
                      </div>
                      {data.as_teammate > 0 && (
                        <div className="text-xs text-muted-foreground">
                          {Math.round(
                            data.teammate_win_rate * data.as_teammate
                          )}
                          W -{" "}
                          {data.as_teammate -
                            Math.round(
                              data.teammate_win_rate * data.as_teammate
                            )}
                          L
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <span
                        className={cn(
                          "font-medium",
                          data.avg_kda >= 4
                            ? "text-purple-600"
                            : data.avg_kda >= 3
                            ? "text-blue-600"
                            : data.avg_kda >= 2
                            ? "text-green-600"
                            : "text-muted-foreground"
                        )}
                      >
                        {data.avg_kda.toFixed(2)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      {onAnalyzePlayer && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onAnalyzePlayer(encounterPuuid)}
                          className="h-8"
                        >
                          <TrendingUp className="h-3 w-3 mr-1" />
                          Analyze
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>

        {sortedEncounters.some(([, data]) => getSuspicionIndicator(data)) && (
          <Alert className="mt-4 border-yellow-200 bg-yellow-50">
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
            <AlertDescription className="text-yellow-800">
              <strong>Suspicious patterns detected.</strong> High win rates with
              specific players may indicate duo queue abuse or potential smurf
              networks. Use the Analyze button to investigate further.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
