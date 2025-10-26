"use client";

import { useState, useEffect, Suspense, useTransition, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { Player, PlayerSchema } from "@/lib/core/schemas";
import { validatedGet } from "@/lib/core/api";
import { PlayerSearch, PlayerCard, PlayerStats } from "@/features/players";
import { MatchHistory, RecentOpponents } from "@/features/matches";
import { PlayerAnalysis } from "@/features/player-analysis";
import { ProtectedRoute } from "@/features/auth";
import { ThemeToggle } from "@/components/theme-toggle";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  PlayerCardSkeleton,
  MatchHistorySkeleton,
  PlayerAnalysisSkeleton,
} from "@/components/loading-skeleton";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";

// TODO [SPY-68]: Add PUUID to URL after a player is selected (same as the redirect from Tracked Players),
// so the player's data stays loaded until user goes to another page, and i.e. refresh won't force
// you to search for player again
export default function PlayerAnalysisPage() {
  const searchParams = useSearchParams();
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [isPending, startTransition] = useTransition();
  const loadedPuuidRef = useRef<string | null>(null);

  // Fetch player data if puuid is provided in URL
  useEffect(() => {
    const puuid = searchParams.get("puuid");
    // Only load if we have a puuid, haven't loaded it yet, and don't have a selected player
    if (puuid && loadedPuuidRef.current !== puuid && !selectedPlayer) {
      loadedPuuidRef.current = puuid;

      startTransition(() => {
        validatedGet(PlayerSchema, `/players/${puuid}`)
          .then((result) => {
            if (result.success) {
              setSelectedPlayer(result.data);
            } else {
              toast.error("Failed to load player data");
              loadedPuuidRef.current = null;
            }
          })
          .catch((error) => {
            toast.error(`Error loading player: ${error.message}`);
            loadedPuuidRef.current = null;
          });
      });
    }
  }, [searchParams, selectedPlayer]);

  const handlePlayerFound = (player: Player) => {
    setSelectedPlayer(player);
  };

  return (
    <ProtectedRoute>
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6 space-y-6">
          {/* Header Card - Full Width */}
          <Card
            id="header-card"
            className="bg-[#152b56] p-6 text-white dark:bg-[#0a1428]"
          >
            <div className="mb-4 flex items-start justify-between">
              <h1 className="text-2xl font-semibold">Player Analysis</h1>
              <ThemeToggle />
            </div>
            <p className="text-sm leading-relaxed">
              Analyze League of Legends players for smurf behavior using match
              history and performance metrics
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

            {/* Right Column - Player Stats and Analysis */}
            <div className="space-y-6">
              {isPending ? (
                <>
                  <PlayerCardSkeleton />
                  <PlayerCardSkeleton />
                </>
              ) : selectedPlayer ? (
                <>
                  <Suspense fallback={<PlayerCardSkeleton />}>
                    <PlayerCard player={selectedPlayer} />
                  </Suspense>

                  <Suspense fallback={<PlayerCardSkeleton />}>
                    <PlayerStats
                      puuid={selectedPlayer.puuid}
                      queueFilter={420}
                      limit={50}
                    />
                  </Suspense>

                  <Tabs defaultValue="smurf" className="w-full">
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="smurf">Player Analysis</TabsTrigger>
                      <TabsTrigger value="opponents">
                        Recent Opponents
                      </TabsTrigger>
                    </TabsList>
                    <TabsContent value="smurf" className="mt-6">
                      <Suspense fallback={<PlayerAnalysisSkeleton />}>
                        <PlayerAnalysis puuid={selectedPlayer.puuid} />
                      </Suspense>
                    </TabsContent>
                    <TabsContent value="opponents" className="mt-6">
                      <Suspense fallback={<PlayerCardSkeleton />}>
                        <RecentOpponents
                          puuid={selectedPlayer.puuid}
                          limit={10}
                          onAnalyzePlayer={handlePlayerFound}
                        />
                      </Suspense>
                    </TabsContent>
                  </Tabs>
                </>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
