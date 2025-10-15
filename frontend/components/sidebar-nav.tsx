"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Image from "next/image";
import { Menu, X } from "lucide-react";

interface NavItem {
  name: string;
  path: string;
}

const navItems: NavItem[] = [
  { name: "Home", path: "/" },
  { name: "Player Analysis", path: "/player-analysis" },
  { name: "Tracked Players", path: "/tracked-players" },
  { name: "Matchmaking Analysis", path: "/matchmaking-analysis" },
  { name: "Jobs", path: "/jobs" },
];

export function SidebarNav() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setMounted(true);
  }, []);

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
        className={`fixed inset-y-0 left-0 z-40 w-[240px] transform bg-[#0a1428] shadow-xl transition-transform duration-300 ease-in-out md:static md:w-[220px] lg:w-[240px] ${
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
                  src="/logo.png"
                  alt="LeaguEyeSpy Logo"
                  fill
                  sizes="(max-width: 768px) 200px, 180px"
                  className="object-contain"
                  priority
                />
              </div>
              <div className="text-center text-xl font-bold text-white md:hidden">
                LeaguEyeSpy
              </div>
            </Link>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 py-6" suppressHydrationWarning>
            <ul className="space-y-2">
              {navItems.map((item) => (
                <li key={item.name}>
                  <Link
                    href={item.path}
                    onClick={() => setMenuOpen(false)}
                    className={`block border-l-4 px-6 py-3 text-white transition-all duration-300 hover:bg-white/10 ${
                      mounted && isActive(item.path)
                        ? "border-[#cfa93a] bg-white/5"
                        : "border-transparent hover:border-[#cfa93a]/50"
                    }`}
                  >
                    <span
                      suppressHydrationWarning
                      className={`transition-colors duration-300 ${
                        mounted && isActive(item.path)
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

          {/* Footer */}
          <div className="border-t border-white/10 p-6">
            <p className="text-center text-xs leading-relaxed text-white/70">
              © 2025 All rights reserved.
              <br />
              <Link
                href="#"
                className="underline transition-colors duration-300 hover:text-[#cfa93a]"
              >
                License
              </Link>
              {" | "}
              <Link
                href="#"
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
