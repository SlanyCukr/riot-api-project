"use client";

import { useState, Suspense } from "react";
import { Player } from "@/lib/schemas";
import { PlayerSearch } from "@/components/player-search";
import { PlayerCard } from "@/components/player-card";
import { PlayerStats } from "@/components/player-stats";
import { MatchHistory } from "@/components/match-history";
import { PlayerAnalysis } from "@/components/player-analysis";
import { RecentOpponents } from "@/components/recent-opponents";
import { ThemeToggle } from "@/components/theme-toggle";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  PlayerCardSkeleton,
  MatchHistorySkeleton,
  PlayerAnalysisSkeleton,
} from "@/components/loading-skeleton";
import { Card } from "@/components/ui/card";

export default function PlayerAnalysisPage() {
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);

  const handlePlayerFound = (player: Player) => {
    setSelectedPlayer(player);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left Column - Header Card */}
        <div className="space-y-2">
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

          {/* Placeholder text above search */}
          {!selectedPlayer && (
            <div className="py-4 text-center text-base text-muted-foreground">
              Search for a player to view their match history and profile
              analysis
            </div>
          )}

          {/* Player Search */}
          <PlayerSearch onPlayerFound={handlePlayerFound} />
        </div>

        {/* Right Column - Results */}
        <div className="space-y-6 lg:col-span-1">
          {selectedPlayer ? (
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

              <Tabs defaultValue="matches" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="matches">Match History</TabsTrigger>
                  <TabsTrigger value="smurf">Player Analysis</TabsTrigger>
                  <TabsTrigger value="opponents">Recent Opponents</TabsTrigger>
                </TabsList>
                <TabsContent value="matches" className="mt-6">
                  <Suspense fallback={<MatchHistorySkeleton />}>
                    <MatchHistory
                      key={`${selectedPlayer.puuid}-420`}
                      puuid={selectedPlayer.puuid}
                      queueFilter={420}
                    />
                  </Suspense>
                </TabsContent>
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
          ) : (
            <div className="flex min-h-[400px] items-center justify-center rounded-lg border border-dashed">
              <p className="text-center text-muted-foreground">
                Select a player from the search to begin analysis
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
