import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Matchmaking Analysis - League Analysis",
  description: "Advanced matchmaking analysis for League of Legends",
};

export default function MatchmakingAnalysisLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
