import { ThemeToggle } from "@/components/theme-toggle";
import { Card } from "@/components/ui/card";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Matchmaking Analysis - League Eye Spy",
  description: "Advanced matchmaking analysis for League of Legends",
};

export default function MatchmakingAnalysisPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <Card
        id="header-card"
        className="bg-[#152b56] p-6 text-white dark:bg-[#0a1428]"
      >
        <div className="mb-4 flex items-start justify-between">
          <h1 className="text-2xl font-semibold">Matchmaking Analysis</h1>
          <ThemeToggle />
        </div>
        <p className="text-sm leading-relaxed">Coming soon...</p>
      </Card>
    </div>
  );
}
