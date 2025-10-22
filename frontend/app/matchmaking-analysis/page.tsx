"use client";

import { useState, Suspense, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Player } from "@/lib/core/schemas";
import { getPlayerByPuuid } from "@/lib/core/api";
import { PlayerSearch, PlayerCard } from "@/features/players";
import { MatchHistory } from "@/features/matches";
import {
  MatchmakingAnalysis,
  MatchmakingAnalysisResults,
} from "@/features/matchmaking";
import { ThemeToggle } from "@/components/theme-toggle";
import { Card } from "@/components/ui/card";
import {
  PlayerCardSkeleton,
  MatchHistorySkeleton,
} from "@/components/loading-skeleton";

function MatchmakingAnalysisContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const hasLoadedFromUrl = useRef(false);

  // On mount, check if there's a puuid in the URL and fetch player data
  useEffect(() => {
    const puuidFromUrl = searchParams.get("puuid");
    if (puuidFromUrl && !selectedPlayer && !hasLoadedFromUrl.current) {
      hasLoadedFromUrl.current = true;
      getPlayerByPuuid(puuidFromUrl).then((result) => {
        if (result.success) {
          setSelectedPlayer(result.data);
          // Invalidate the MatchmakingAnalysisResults query to ensure it fetches fresh data
          queryClient.invalidateQueries({
            queryKey: ["matchmaking-analysis-results", puuidFromUrl],
          });
        } else {
          console.error("Failed to load player from URL:", result.error);
          // Clear invalid puuid from URL
          router.push("/matchmaking-analysis", { scroll: false });
        }
      });
    }
  }, [searchParams, selectedPlayer, router, queryClient]);

  const handlePlayerFound = (player: Player) => {
    setSelectedPlayer(player);
    // Update URL with puuid parameter
    router.push(`/matchmaking-analysis?puuid=${player.puuid}`, {
      scroll: false,
    });
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6 space-y-6">
        {/* Header Card - Full Width */}
        <Card
          id="header-card"
          className="bg-[#152b56] p-6 text-white dark:bg-[#0a1428]"
        >
          <div className="mb-4 flex items-start justify-between">
            <h1 className="text-2xl font-semibold">Matchmaking Analysis</h1>
            <ThemeToggle />
          </div>
          <p className="text-sm leading-relaxed">
            Analyze matchmaking fairness by comparing average winrates of
            teammates vs enemies in recent ranked matches
          </p>
        </Card>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Left Column - Player Search and Match History */}
          <div className="space-y-6">
            <PlayerSearch onPlayerFound={handlePlayerFound} />

            {selectedPlayer && (
              <Suspense fallback={<MatchHistorySkeleton />}>
                <MatchHistory
                  key={`${selectedPlayer.puuid}-420`}
                  puuid={selectedPlayer.puuid}
                  queueFilter={420}
                />
              </Suspense>
            )}
          </div>

          {/* Right Column - Player Card and Matchmaking Analysis */}
          <div className="space-y-6">
            {selectedPlayer ? (
              <>
                <Suspense fallback={<PlayerCardSkeleton />}>
                  <PlayerCard player={selectedPlayer} />
                </Suspense>
                <MatchmakingAnalysis puuid={selectedPlayer.puuid} />
                <MatchmakingAnalysisResults puuid={selectedPlayer.puuid} />
              </>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MatchmakingAnalysisPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <MatchmakingAnalysisContent />
    </Suspense>
  );
}
