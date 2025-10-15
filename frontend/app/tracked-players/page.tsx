"use client";

import { AddTrackedPlayer } from "@/components/add-tracked-player";
import { TrackedPlayersList } from "@/components/tracked-players-list";
import { ThemeToggle } from "@/components/theme-toggle";
import { Card } from "@/components/ui/card";

export default function TrackedPlayersPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6 space-y-6">
        {/* Header Card */}
        <Card className="bg-[#2c3e6f] p-6 text-white dark:bg-[#151e46]">
          <div className="mb-4 flex items-start justify-between">
            <h1 className="text-2xl font-medium text-[#c8aa6e]">
              Tracked Players
            </h1>
            <ThemeToggle />
          </div>
          <p className="text-sm leading-relaxed">
            Track League of Legends players for automated match history updates
            and continuous monitoring. Tracked players are automatically updated
            every 2 minutes by background jobs.
          </p>
        </Card>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Left Column - Add Tracked Player Form */}
          <div className="space-y-6">
            <AddTrackedPlayer />
          </div>

          {/* Right Column - Tracked Players List */}
          <div className="space-y-6">
            <TrackedPlayersList />
          </div>
        </div>
      </div>
    </div>
  );
}
