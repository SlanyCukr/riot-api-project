"use client";

import { ThemeToggle } from "@/components/theme-toggle";
import { ProtectedRoute } from "@/features/auth";

export default function Home() {
  return (
    <ProtectedRoute>
      <div className="container mx-auto max-w-4xl px-4 py-8">
        <div className="mb-8 flex items-start justify-between">
          <h1 className="text-4xl font-bold text-[#0a1428] dark:text-[#cfa93a]">
            League Eye Spy
          </h1>
          <ThemeToggle />
        </div>

        <div className="prose prose-lg max-w-none space-y-4 text-foreground/80">
          <p className="leading-relaxed">
            Welcome to League Eye Spy - your comprehensive tool for analyzing
            League of Legends match data and detecting suspicious player
            behavior. Our advanced algorithms help identify smurfs, boosted
            accounts, and unusual gameplay patterns.
          </p>
          <p className="leading-relaxed">
            Using data from the Riot Games API, we track player performance
            metrics, match history, and rank progression to provide detailed
            insights into player behavior. Whether you&apos;re curious about a
            teammate, investigating a suspicious opponent, or just exploring
            match data, League Eye Spy gives you the tools you need.
          </p>
          <p className="leading-relaxed">
            Our player analysis system examines multiple factors including win
            rates, KDA ratios, champion mastery progression, and rank climb
            velocity. Combined with match history analysis, we can identify
            patterns that suggest an account is being piloted by a player of
            significantly different skill level.
          </p>
          <p className="leading-relaxed">
            Get started by navigating to the Player Analysis page to search for
            a player and view their detailed analysis. Our real-time data
            fetching ensures you always have access to the most up-to-date
            information available.
          </p>
        </div>
      </div>
    </ProtectedRoute>
  );
}
