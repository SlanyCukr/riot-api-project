import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Jobs - League Analysis",
  description:
    "Monitor and manage background jobs for player tracking and data updates",
};

export default function JobsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
