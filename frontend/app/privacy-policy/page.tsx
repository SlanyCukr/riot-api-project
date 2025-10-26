"use client";

import { ThemeToggle } from "@/components/theme-toggle";
import { ProtectedRoute } from "@/features/auth";
import { Card, CardContent } from "@/components/ui/card";

export default function PrivacyPolicyPage() {
  return (
    <ProtectedRoute>
      <div className="container mx-auto max-w-4xl px-4 py-8">
        <Card id="header-card" className="py-2">
          <div className="flex flex-col">
            <div className="px-8 pt-4 pb-2 flex items-start justify-between">
              <h1 className="text-3xl font-[family-name:var(--font-league)]">
                Privacy Policy
              </h1>
              <ThemeToggle />
            </div>
          </div>
          <CardContent className="px-8 pt-0 pb-4 prose prose-lg max-w-none space-y-4">
            <p className="leading-relaxed">
              League Analysis respects your privacy and is committed to
              protecting your personal information.
            </p>

            <h2 className="text-2xl font-semibold mt-6 mb-3">
              Information We Collect
            </h2>
            <p className="leading-relaxed">
              We collect and process League of Legends player data through the
              Riot Games API, including summoner names, match history,
              performance statistics, and rank information. This data is used
              solely for the purpose of providing analysis and insights within
              the application.
            </p>

            <h2 className="text-2xl font-semibold mt-6 mb-3">
              How We Use Your Data
            </h2>
            <p className="leading-relaxed">
              The data collected is used exclusively to:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                Provide player analysis and account anomaly detection services
              </li>
              <li>Display match history and performance statistics</li>
              <li>Track player rank progression and metrics</li>
              <li>Generate matchmaking analysis reports</li>
            </ul>

            <h2 className="text-2xl font-semibold mt-6 mb-3">
              Data Storage and Security
            </h2>
            <p className="leading-relaxed">
              All data is stored securely and is only accessible to
              authenticated users of the application. We do not share, sell, or
              distribute your data to third parties.
            </p>

            <h2 className="text-2xl font-semibold mt-6 mb-3">Your Rights</h2>
            <p className="leading-relaxed">
              You have the right to request deletion of your tracked player data
              at any time through the application interface. Public match data
              from the Riot Games API cannot be deleted as it is publicly
              available information.
            </p>

            <h2 className="text-2xl font-semibold mt-6 mb-3">Contact</h2>
            <p className="leading-relaxed">
              If you have any questions or concerns about our privacy practices,
              please contact the application administrators.
            </p>

            <p className="leading-relaxed text-sm mt-8 text-center">
              © 2025 Marek Hovadík & Matěj Kadlec. All rights reserved.
            </p>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  );
}
