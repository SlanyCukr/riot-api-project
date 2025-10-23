"use client";

import { ThemeToggle } from "@/components/theme-toggle";
import { ProtectedRoute } from "@/features/auth";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function Home() {
  return (
    <ProtectedRoute>
      <div className="container mx-auto max-w-4xl px-4 py-8">
        <div className="mb-8 flex justify-end">
          <ThemeToggle />
        </div>

        <Card>
          <CardHeader>
            <h1
              className="text-4xl font-bold mb-4"
              style={{
                backgroundImage:
                  "linear-gradient(180deg, #f2d777 0%, #cfa93a 60%, #9d7d22 100%)",
                backgroundClip: "text",
                WebkitBackgroundClip: "text",
                color: "transparent",
              }}
            >
              League Eye Spy
            </h1>
            <h2 className="text-2xl font-semibold">Welcome</h2>
          </CardHeader>
          <CardContent className="prose prose-lg max-w-none space-y-4">
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
