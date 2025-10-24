import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Tracked Players - League Analysis",
  description:
    "Track League of Legends players for automated match history updates and continuous monitoring",
};

export default function TrackedPlayersLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
