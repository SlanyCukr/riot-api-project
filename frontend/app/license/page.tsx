"use client";

import { ThemeToggle } from "@/components/theme-toggle";
import { ProtectedRoute } from "@/features/auth";
import { Card, CardContent } from "@/components/ui/card";

export default function LicensePage() {
  return (
    <ProtectedRoute>
      <div className="container mx-auto max-w-4xl px-4 py-8">
        <Card id="header-card" className="py-2">
          <div className="flex flex-col">
            <div className="px-8 pt-4 pb-2 flex items-start justify-between">
              <h1 className="text-3xl font-[family-name:var(--font-league)]">
                License
              </h1>
              <ThemeToggle />
            </div>
          </div>
          <CardContent className="px-8 pt-0 pb-4 prose prose-lg max-w-none space-y-4">
            <p className="leading-relaxed">
              League Analysis is a proprietary application developed for
              analyzing League of Legends player data and match statistics.
            </p>

            <h2 className="text-2xl font-semibold mt-6 mb-3">Terms of Use</h2>
            <p className="leading-relaxed">
              This application is provided for personal and educational use. By
              using League Analysis, you agree to use the service responsibly
              and in accordance with Riot Games&apos; Terms of Service and API
              Usage Policy.
            </p>

            <h2 className="text-2xl font-semibold mt-6 mb-3">Data Source</h2>
            <p className="leading-relaxed">
              League Analysis uses data from the Riot Games API. League Analysis
              isn&apos;t endorsed by Riot Games and doesn&apos;t reflect the
              views or opinions of Riot Games or anyone officially involved in
              producing or managing Riot Games properties. Riot Games, and all
              associated properties are trademarks or registered trademarks of
              Riot Games, Inc.
            </p>

            <h2 className="text-2xl font-semibold mt-6 mb-3">Disclaimer</h2>
            <p className="leading-relaxed">
              The analysis and predictions provided by this application are for
              informational purposes only. We do not guarantee the accuracy or
              completeness of any information or analysis provided through this
              service.
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
