import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  const navItems = [
    { name: "Home", path: "/" },
    { name: "Smurf Detection", path: "/smurf-detection" },
    { name: "Boosted Detection", path: "/" }, // Dummy link
    { name: "Matchmaking Analysis", path: "/" }, // Dummy link
  ];

  const isActive = (path: string) => {
    if (path === "/") {
      return location.pathname === "/";
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="flex min-h-screen">
      {/* Mobile Hamburger Button */}
      <button
        className="fixed top-4 left-4 z-50 md:hidden bg-navy-base text-white p-2 rounded-md shadow-lg hover:bg-navy-dark transition-colors"
        onClick={() => setMenuOpen(!menuOpen)}
        aria-label="Toggle menu"
      >
        <svg
          className="w-6 h-6"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          {menuOpen ? (
            <path d="M6 18L18 6M6 6l12 12" />
          ) : (
            <path d="M4 6h16M4 12h16M4 18h16" />
          )}
        </svg>
      </button>

      {/* Sidebar Menu */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-[260px] lg:w-[260px] md:w-[220px] bg-navy-base shadow-xl transform transition-transform duration-300 ease-in-out ${
          menuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo Section */}
          <div className="p-6 border-b border-white/10">
            <Link
              to="/"
              className="block cursor-pointer hover:opacity-80 transition-opacity duration-300"
              onClick={() => setMenuOpen(false)}
            >
              <img
                src="/image/logo.png"
                alt="LeagueYesPy Logo"
                className="w-full max-w-[200px] md:max-w-[180px] mx-auto hidden md:block"
              />
              <div className="md:hidden text-white text-xl font-bold text-center">
                LeagueYesPy
              </div>
            </Link>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 py-6">
            <ul className="space-y-2">
              {navItems.map((item) => (
                <li key={item.name}>
                  <Link
                    to={item.path}
                    onClick={() => setMenuOpen(false)}
                    className={`block px-6 py-3 text-white transition-all duration-300 hover:bg-white/10 border-l-4 ${
                      isActive(item.path)
                        ? "bg-white/5 border-gold-base"
                        : "border-transparent hover:border-gold-base/50"
                    }`}
                  >
                    <span
                      className={`transition-colors duration-300 ${
                        isActive(item.path)
                          ? "text-gold-base"
                          : "hover:text-gold-base"
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
          <div className="p-6 border-t border-white/10">
            <p className="text-white/70 text-xs text-center leading-relaxed">
              © 2025 All rights reserved.
              <br />
              <a
                href="/"
                className="hover:text-gold-base transition-colors duration-300 underline"
              >
                License
              </a>
              {" | "}
              <a
                href="/"
                className="hover:text-gold-base transition-colors duration-300 underline"
              >
                Privacy Policy
              </a>
            </p>
          </div>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {menuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setMenuOpen(false)}
        />
      )}

      {/* Main Content Area */}
      <main className="flex-1 bg-white min-h-screen">{children}</main>
    </div>
  );
}
