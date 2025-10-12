"use client";

import { useQuery } from "@tanstack/react-query";
import { MatchListResponseSchema } from "@/lib/schemas";
import { validatedGet } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { History, AlertCircle } from "lucide-react";

interface MatchHistoryProps {
  puuid: string;
  queueFilter?: number;
}

export function MatchHistory({ puuid, queueFilter = 420 }: MatchHistoryProps) {
  const {
    data: response,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["matchHistory", puuid, queueFilter],
    queryFn: () =>
      validatedGet(MatchListResponseSchema, "/matches", {
        puuid,
        queue_id: queueFilter,
        start: 0,
        count: 20,
      }),
  });

  const data = response?.success ? response.data : null;

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
    const errorMessage =
      error instanceof Error
        ? error.message
        : response && !response.success
          ? response.error.message
          : "Failed to load matches";

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
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.matches.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Match History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground">
            No matches found for this player
          </p>
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
          <Badge variant="secondary">{data.total} matches</Badge>
        </div>
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
              {data.matches.map((match) => (
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
      </CardContent>
    </Card>
  );
}
