import type { Metadata } from "next";
import { Montserrat } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { ThemeProvider } from "@/components/theme-provider";
import { SidebarNav } from "@/components/sidebar-nav";
import { Toaster } from "sonner";

const montserrat = Montserrat({
  subsets: ["latin"],
  weight: ["100", "200", "300", "400", "500", "600", "700", "800", "900"],
  style: ["normal", "italic"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "League Eye Spy",
  description:
    "Analyze League of Legends players for smurf behavior using match history and performance metrics",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${montserrat.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <Providers>
            <div className="flex min-h-screen">
              <SidebarNav />
              <main className="flex-1 bg-background">{children}</main>
            </div>
            <Toaster position="top-right" richColors />
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  );
}
