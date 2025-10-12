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

export default function Home() {
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);

  const handlePlayerFound = (player: Player) => {
    setSelectedPlayer(player);
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8 flex items-start justify-between">
          <div className="flex-1 text-center">
            <h1 className="mb-2 text-4xl font-bold">
              Riot API Smurf Detection
            </h1>
            <p className="text-muted-foreground">
              Analyze League of Legends players for smurf behavior using match
              history and performance metrics
            </p>
          </div>
          <ThemeToggle />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Search Column */}
          <div className="lg:col-span-1">
            <PlayerSearch onPlayerFound={handlePlayerFound} />
          </div>

          {/* Results Column */}
          <div className="space-y-6 lg:col-span-2">
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
                  Search for a player to view their match history and smurf
                  detection analysis
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
