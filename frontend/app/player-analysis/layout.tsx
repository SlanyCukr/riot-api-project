import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Player Analysis - League Eye Spy",
  description:
    "Analyze League of Legends players for smurf behavior using match history and performance metrics",
};

export default function PlayerAnalysisLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
