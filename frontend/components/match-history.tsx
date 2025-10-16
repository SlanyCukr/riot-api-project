"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { History, AlertCircle, Loader2 } from "lucide-react";

import { MatchListResponseSchema } from "@/lib/schemas";
import { validatedGet } from "@/lib/api";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface MatchHistoryProps {
  puuid: string;
  queueFilter?: number;
}

export function MatchHistory({ puuid, queueFilter = 420 }: MatchHistoryProps) {
  const PAGE_SIZE = 50;
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const previousMatchCount = useRef(0);

  const [displayCount, setDisplayCount] = useState(50);

  // Reset when player/queue changes
  useEffect(() => {
    setDisplayCount(50);
    previousMatchCount.current = 0;
  }, [puuid, queueFilter]);

  const {
    data: response,
    isLoading,
    error,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ["matchHistory", puuid, queueFilter, displayCount],
    queryFn: async () => {
      const result = await validatedGet(
        MatchListResponseSchema,
        `/matches/player/${puuid}`,
        {
          queue: queueFilter,
          start: 0,
          count: displayCount,
        },
      );

      return result;
    },
    enabled: !!puuid,
    retry: 2,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    placeholderData: (previousData) => previousData,
    staleTime: 60000,
  });

  const data = response?.success ? response.data : null;

  const allMatches = data?.matches || [];
  const totalMatches = data?.total || 0;
  const hasMore = allMatches.length < totalMatches;

  // Preserve scroll position when new matches load
  useEffect(() => {
    if (
      allMatches.length > previousMatchCount.current &&
      previousMatchCount.current > 0
    ) {
      previousMatchCount.current = allMatches.length;
    } else if (allMatches.length > 0) {
      previousMatchCount.current = allMatches.length;
    }
  }, [allMatches.length]);

  const loadMore = useCallback(() => {
    if (!isFetching && hasMore) {
      setDisplayCount((prev) => prev + PAGE_SIZE);
    }
  }, [isFetching, hasMore, PAGE_SIZE]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const first = entries[0];
        if (first.isIntersecting) {
          loadMore();
        }
      },
      { threshold: 0.1, rootMargin: "100px" },
    );

    const currentRef = loadMoreRef.current;
    if (currentRef) {
      observer.observe(currentRef);
    }

    return () => {
      if (currentRef) {
        observer.unobserve(currentRef);
      }
    };
  }, [loadMore]);

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const getQueueName = (queueId: number) => {
    const queues: Record<number, string> = {
      420: "Ranked Solo/Duo",
      440: "Ranked Flex",
      400: "Normal Draft",
      430: "Normal Blind",
      450: "ARAM",
    };
    return queues[queueId] || `Queue ${queueId}`;
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Match History
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || (response && !response.success)) {
    const errorObj =
      error instanceof Error
        ? error
        : response && !response.success
          ? response.error
          : null;

    const errorMessage = errorObj
      ? typeof errorObj === "object" && "message" in errorObj
        ? errorObj.message
        : String(errorObj)
      : "Failed to load matches";

    const isNotFound =
      errorMessage.toLowerCase().includes("not found") ||
      (typeof errorObj === "object" &&
        errorObj &&
        "status" in errorObj &&
        errorObj.status === 404);

    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Match History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {isNotFound ? (
                <div className="space-y-2">
                  <p>No match history found for this player.</p>
                  <p className="text-sm text-muted-foreground">
                    This could mean the player has no ranked games, or match
                    data is not yet available.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  <p>{errorMessage}</p>
                  <Button
                    onClick={() => refetch()}
                    variant="outline"
                    size="sm"
                    className="mt-2"
                  >
                    Retry
                  </Button>
                </div>
              )}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!isLoading && allMatches.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Match History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <p className="font-medium">No matches available yet</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Matches will appear here as background jobs fetch them from the
                Riot API. This may take a few minutes for new players.
              </p>
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Match History
          </CardTitle>
          <Badge variant="secondary">{totalMatches} matches in database</Badge>
        </div>
        {totalMatches > 0 && totalMatches < 50 && (
          <p className="mt-2 text-xs text-muted-foreground">
            More matches are being fetched in the background
          </p>
        )}
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Queue</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Version</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {allMatches.map((match) => (
                <TableRow key={match.match_id}>
                  <TableCell className="font-medium">
                    {getQueueName(match.queue_id)}
                  </TableCell>
                  <TableCell>{formatDate(match.game_creation)}</TableCell>
                  <TableCell>{formatDuration(match.game_duration)}</TableCell>
                  <TableCell>
                    <span className="font-mono text-xs">
                      {match.patch_version ||
                        match.game_version.split(".").slice(0, 2).join(".")}
                    </span>
                  </TableCell>
                  <TableCell>
                    {match.is_processed ? (
                      <Badge variant="default">Processed</Badge>
                    ) : (
                      <Badge variant="secondary">Pending</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        {hasMore && (
          <div ref={loadMoreRef} className="mt-4 flex justify-center py-4">
            {isFetching ? (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Loading more matches...</span>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">
                Showing {allMatches.length} of {totalMatches} matches
              </div>
            )}
          </div>
        )}
        {!hasMore && allMatches.length > 0 && (
          <div className="mt-4 flex justify-center py-4">
            <div className="text-sm text-muted-foreground">
              All {totalMatches} matches loaded
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
