"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { History, AlertCircle, Loader2 } from "lucide-react";

import { MatchListResponseSchema } from "@/lib/core/schemas";
import { validatedGet } from "@/lib/core/api";

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

// TODO: [SPY-64]
// 1. Show less matches on initial load (10/15/20).
// 2. Make the component scrollable, so the user scrolls through the component, rather than through
// whole page. This ensures that other components will be shown on the page, as well as the sidebar
// footer, which currently dissappears when the MatchHistoy is shown, and scrolling down pushes it
// down as well, making it impossible to see it for th user.
// 3. Ensure the sidebar footer is shown even if this component goes off the page, this is probably
// more of a sidebar problem, but as it's closely related to this, and will be most likely quick
// fix, we can do it in one ticket
export function MatchHistory({ puuid, queueFilter = 420 }: MatchHistoryProps) {
  const PAGE_SIZE = 50;
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const previousMatchCount = useRef(0);

  // Component uses key={`${puuid}-${queueFilter}`} to reset state on prop changes
  // This avoids calling setState in useEffect which violates React Compiler rules
  const [displayCount, setDisplayCount] = useState(50);

  const {
    data: response,
    isLoading,
    error,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ["matchHistory", puuid, queueFilter, displayCount],
    queryFn: async () => {
      try {
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
      } catch (err) {
        // Handle network errors gracefully
        console.debug("Match history fetch error:", err);
        throw err;
      }
    },
    enabled: !!puuid,
    retry: (failureCount, error) => {
      // Don't retry on network errors, but allow retries on other errors
      if (
        error instanceof Error &&
        (error.message.includes("Network Error") ||
          error.message.includes("ERR_NETWORK"))
      ) {
        return false;
      }
      return failureCount < 2;
    },
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
  }, [isFetching, hasMore]);

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
            <History className="h-5 w-5 text-primary" />
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
    let errorMessage = "Failed to load matches";

    if (error instanceof Error) {
      errorMessage = error.message;
    } else if (response && !response.success && response.error) {
      errorMessage =
        typeof response.error === "object" && "message" in response.error
          ? response.error.message
          : String(response.error);
    }

    // Handle specific network error messages
    if (
      errorMessage.includes("Network Error") ||
      errorMessage.includes("ERR_NETWORK")
    ) {
      errorMessage =
        "Network connection failed. Please check your internet connection.";
    }

    const isNotFound =
      errorMessage.toLowerCase().includes("not found") ||
      (error instanceof Error && error.message.includes("404"));

    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5 text-primary" />
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
                    type="submit"
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
            <History className="h-5 w-5 text-primary" />
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
            <History className="h-5 w-5 text-primary" />
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
