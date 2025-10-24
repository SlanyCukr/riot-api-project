"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Image from "next/image";
import { Menu, X, User, LogOut, Settings, Wrench } from "lucide-react";
import { useAuth } from "@/features/auth";

interface NavItem {
  name: string;
  path: string;
}

const navItems: NavItem[] = [
  { name: "Home", path: "/" },
  { name: "Player Analysis", path: "/player-analysis" },
  { name: "Matchmaking Analysis", path: "/matchmaking-analysis" },
  { name: "Tracked Players", path: "/tracked-players" },
];

export function SidebarNav() {
  const [menuOpen, setMenuOpen] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuth();

  // Hide sidebar on sign-in page
  if (pathname === "/sign-in") {
    return null;
  }

  const isActive = (path: string) => {
    if (path === "/") {
      return pathname === "/";
    }
    return pathname.startsWith(path);
  };

  return (
    <>
      {/* Mobile Hamburger Button */}
      <button
        className="fixed left-4 top-4 z-50 rounded-md bg-[#0a1428] p-2 text-white shadow-lg transition-colors hover:bg-[#0d1a33] md:hidden"
        onClick={() => setMenuOpen(!menuOpen)}
        aria-label="Toggle menu"
      >
        {menuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
      </button>

      {/* Sidebar Menu */}
      <aside
        suppressHydrationWarning
        style={{ backgroundColor: "#0a1428" }}
        className={`fixed inset-y-0 left-0 z-40 w-[240px] transform shadow-xl transition-transform duration-300 ease-in-out md:sticky md:top-0 md:h-screen md:w-[220px] lg:w-[240px] ${
          menuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <div className="flex h-full flex-col">
          {/* Logo Section */}
          <div className="border-b border-white/10 p-6">
            <Link
              href="/"
              className="block cursor-pointer transition-opacity duration-300 hover:opacity-80"
              onClick={() => setMenuOpen(false)}
            >
              <div className="relative mx-auto hidden h-[60px] w-full max-w-[200px] md:block md:max-w-[180px]">
                <Image
                  src="/logo-v3.png"
                  alt="League Analysis Logo"
                  fill
                  sizes="(max-width: 768px) 200px, 180px"
                  className="object-contain"
                  priority
                />
              </div>
              <div className="text-center text-xl font-bold text-white md:hidden">
                League Analysis
              </div>
            </Link>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 py-6 overflow-y-auto" suppressHydrationWarning>
            <ul className="space-y-2">
              {navItems.map((item) => (
                <li key={item.name}>
                  <Link
                    href={item.path}
                    onClick={() => setMenuOpen(false)}
                    className={`block border-l-4 px-6 py-3 text-white transition-all duration-300 hover:bg-white/10 ${
                      isActive(item.path)
                        ? "border-[#cfa93a] bg-white/5"
                        : "border-transparent hover:border-[#cfa93a]/50"
                    }`}
                  >
                    <span
                      suppressHydrationWarning
                      className={`transition-colors duration-300 ${
                        isActive(item.path)
                          ? "text-[#cfa93a] font-medium"
                          : "hover:text-[#cfa93a]"
                      }`}
                    >
                      {item.name}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          {/* User Info and Bottom Links */}
          {user && (
            <div className="border-t border-white/10">
              <div className="text-xs">
                <div className="flex items-center gap-2 text-white p-4 pb-2">
                  <User className="h-4 w-4 text-[#cfa93a]" />
                  <p className="font-medium">{user.display_name}</p>
                </div>

                <Link
                  href="/jobs"
                  onClick={() => setMenuOpen(false)}
                  className={`flex items-center gap-2 px-4 py-2 text-white cursor-pointer transition-colors duration-300 hover:text-[#cfa93a] ${
                    isActive("/jobs") ? "text-[#cfa93a] font-medium" : ""
                  }`}
                >
                  <Wrench className="h-4 w-4 text-[#cfa93a]" />
                  Jobs
                </Link>

                <Link
                  href="/settings"
                  onClick={() => setMenuOpen(false)}
                  className={`flex items-center gap-2 px-4 py-2 text-white cursor-pointer transition-colors duration-300 hover:text-[#cfa93a] ${
                    isActive("/settings") ? "text-[#cfa93a] font-medium" : ""
                  }`}
                >
                  <Settings className="h-4 w-4 text-[#cfa93a]" />
                  Settings
                </Link>

                <button
                  onClick={logout}
                  className="flex items-center gap-2 px-4 py-2 pb-4 text-white cursor-pointer transition-colors duration-300 hover:text-[#cfa93a] w-full text-left"
                >
                  <LogOut className="h-4 w-4 text-[#cfa93a] scale-x-[-1]" />
                  Sign Out
                </button>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="border-t border-white/10 p-6">
            <p className="text-center text-xs leading-relaxed text-white/70">
              © 2025 All rights reserved.
              <br />
              <Link
                href="/license"
                className="underline transition-colors duration-300 hover:text-[#cfa93a]"
              >
                License
              </Link>
              {" | "}
              <Link
                href="/privacy-policy"
                className="underline transition-colors duration-300 hover:text-[#cfa93a]"
              >
                Privacy Policy
              </Link>
            </p>
          </div>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {menuOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setMenuOpen(false)}
        />
      )}
    </>
  );
}
