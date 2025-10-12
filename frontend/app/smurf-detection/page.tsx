"use client";

import { useState, Suspense } from "react";
import { Player } from "@/lib/schemas";
import { PlayerSearch } from "@/components/player-search";
import { PlayerCard } from "@/components/player-card";
import { MatchHistory } from "@/components/match-history";
import { SmurfDetection } from "@/components/smurf-detection";
import { ThemeToggle } from "@/components/theme-toggle";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  PlayerCardSkeleton,
  MatchHistorySkeleton,
  SmurfDetectionSkeleton,
} from "@/components/loading-skeleton";
import { Card } from "@/components/ui/card";

export default function SmurfDetectionPage() {
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);

  const handlePlayerFound = (player: Player) => {
    setSelectedPlayer(player);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left Column - Header Card */}
        <div className="space-y-2">
          <Card className="bg-[#2c3e6f] p-6 text-white dark:bg-[#151e46]">
            <div className="mb-4 flex items-start justify-between">
              <h1 className="text-2xl font-medium text-[#c8aa6e]">
                Smurf Detection
              </h1>
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
              Search for a player to view their match history and smurf
              detection analysis
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

              <Tabs defaultValue="matches" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="matches">Match History</TabsTrigger>
                  <TabsTrigger value="smurf">Smurf Detection</TabsTrigger>
                </TabsList>
                <TabsContent value="matches" className="mt-6">
                  <Suspense fallback={<MatchHistorySkeleton />}>
                    <MatchHistory
                      puuid={selectedPlayer.puuid}
                      queueFilter={420}
                    />
                  </Suspense>
                </TabsContent>
                <TabsContent value="smurf" className="mt-6">
                  <Suspense fallback={<SmurfDetectionSkeleton />}>
                    <SmurfDetection puuid={selectedPlayer.puuid} />
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
