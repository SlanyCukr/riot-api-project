"use client";

import Image from "next/image";
import { ThemeToggle } from "@/components/theme-toggle";
import { ProtectedRoute } from "@/features/auth";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function Home() {
  return (
    <ProtectedRoute>
      <div className="container mx-auto max-w-4xl px-4 py-8">
        <Card id="header-card" className="py-2">
          <div className="flex flex-col">
            <div className="px-8 pt-4 pb-2 flex items-start justify-between">
              <div className="flex items-center gap-3">
                <h1 className="text-4xl font-[family-name:var(--font-league)]">
                  League Analysis
                </h1>
                <div className="relative h-[3.5rem] w-[3.5rem] -m-t-2 -m-b-3">
                  <Image
                    src="/magnifier.png"
                    alt="Magnifier"
                    fill
                    className="object-contain"
                  />
                </div>
              </div>
              <ThemeToggle />
            </div>
          </div>
          <CardContent className="px-8 pt-0 pb-4 prose prose-lg max-w-none space-y-4">
            <p className="leading-relaxed">
              Welcome to League Analysis - your comprehensive tool for analyzing
              League of Legends match data and detecting suspicious player
              behavior. Our advanced algorithms help identify smurfs, boosted
              accounts, and unusual gameplay patterns.
            </p>
            <p className="leading-relaxed">
              Using data from the Riot Games API, we track player performance
              metrics, match history, and rank progression to provide detailed
              insights into player behavior. Whether you&apos;re curious about a
              teammate, investigating a suspicious opponent, or just exploring
              match data, League Analysis gives you the tools you need.
            </p>
            <p className="leading-relaxed">
              Our player analysis system examines multiple factors including win
              rates, KDA ratios, champion mastery progression, and rank climb
              velocity. Combined with match history analysis, we can identify
              patterns that suggest an account is being piloted by a player of
              significantly different skill level.
            </p>
            <p className="leading-relaxed">
              Get started by navigating to the Player Analysis page to search
              for a player and view their detailed analysis. Our real-time data
              fetching ensures you always have access to the most up-to-date
              information available.
            </p>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  );
}
