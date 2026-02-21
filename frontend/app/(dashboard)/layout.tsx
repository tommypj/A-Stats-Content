"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  Sparkles,
  Image as ImageIcon,
  BarChart3,
  Settings,
  Menu,
  X,
  LogOut,
  ChevronDown,
  ChevronUp,
  Share2,
  Calendar,
  History,
  Edit3,
  Users,
  BookOpen,
  Shield,
  Globe,
  Zap,
  FileSearch,
} from "lucide-react";
import { clsx } from "clsx";
import { TeamProvider } from "@/contexts/TeamContext";
import { TeamSwitcher } from "@/components/team/team-switcher";
import { api, UserResponse } from "@/lib/api";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Outlines", href: "/outlines", icon: FileText },
  { name: "Articles", href: "/articles", icon: Sparkles },
  { name: "Images", href: "/images", icon: ImageIcon },
  {
    name: "Social",
    icon: Share2,
    submenu: [
      { name: "Dashboard", href: "/social", icon: LayoutDashboard },
      { name: "Compose", href: "/social/compose", icon: Edit3 },
      { name: "Calendar", href: "/social/calendar", icon: Calendar },
      { name: "History", href: "/social/history", icon: History },
      { name: "Accounts", href: "/social/accounts", icon: Users },
    ],
  },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Knowledge", href: "/knowledge", icon: BookOpen },
  { name: "Teams", href: "/teams", icon: Users },
];

function DashboardContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [expandedMenus, setExpandedMenus] = useState<Set<string>>(new Set(["Social"]));
  const [user, setUser] = useState<UserResponse | null>(null);

  useEffect(() => {
    const loadUser = async () => {
      try {
        const data = await api.auth.me();
        setUser(data);
      } catch {
        // Not logged in
      }
    };
    loadUser();
  }, []);

  const handleSignOut = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("refresh_token");
    router.push("/login");
  };

  const isAdmin = user?.role === "admin" || user?.role === "super_admin";
  const userInitials = user?.name
    ? user.name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : "U";

  return (
    <div className="min-h-screen bg-surface-secondary">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar - Dark sage theme */}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 w-64 bg-primary-950 transform transition-transform duration-200 ease-in-out lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex h-16 items-center justify-between px-4 border-b border-primary-800">
            <Link href="/dashboard" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-primary-700 flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-cream-200" />
              </div>
              <div>
                <span className="font-display text-lg font-semibold text-cream-100">
                  A-Stats
                </span>
                <p className="text-xs text-primary-400">Relational SEO</p>
              </div>
            </Link>
            <div className="h-8 w-8 rounded-lg bg-amber-600/20 border border-amber-600/40 flex items-center justify-center">
              <Shield className="h-4 w-4 text-amber-500" />
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1 rounded-lg hover:bg-primary-800"
            >
              <X className="h-5 w-5 text-cream-300" />
            </button>
          </div>

          {/* Team Switcher */}
          <div className="px-3 py-4 border-b border-primary-800">
            <TeamSwitcher />
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => {
              // Item with submenu
              if ("submenu" in item) {
                const isExpanded = expandedMenus.has(item.name);
                const hasActiveChild = item.submenu?.some((subItem) =>
                  pathname.startsWith(subItem.href)
                );

                return (
                  <div key={item.name}>
                    <button
                      onClick={() => {
                        const newExpanded = new Set(expandedMenus);
                        if (isExpanded) {
                          newExpanded.delete(item.name);
                        } else {
                          newExpanded.add(item.name);
                        }
                        setExpandedMenus(newExpanded);
                      }}
                      className={clsx(
                        "flex w-full items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                        hasActiveChild
                          ? "bg-primary-800 text-cream-50"
                          : "text-cream-300 hover:bg-primary-900 hover:text-cream-100"
                      )}
                    >
                      <item.icon className="h-5 w-5" />
                      <span className="flex-1 text-left">{item.name}</span>
                      <ChevronDown
                        className={clsx(
                          "h-4 w-4 transition-transform",
                          isExpanded && "rotate-180"
                        )}
                      />
                    </button>
                    {isExpanded && (
                      <div className="mt-1 ml-3 pl-3 border-l-2 border-primary-700 space-y-1">
                        {item.submenu?.map((subItem) => {
                          const isActive = pathname === subItem.href;
                          return (
                            <Link
                              key={subItem.name}
                              href={subItem.href}
                              className={clsx(
                                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                                isActive
                                  ? "bg-primary-800 text-cream-50"
                                  : "text-cream-300 hover:bg-primary-900 hover:text-cream-100"
                              )}
                            >
                              <subItem.icon className="h-4 w-4" />
                              {subItem.name}
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              }

              // Regular item
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={clsx(
                    "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary-800 text-cream-50"
                      : "text-cream-300 hover:bg-primary-900 hover:text-cream-100"
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* User card + floating submenu */}
          <div className="relative border-t border-primary-800">
            {/* Floating popover - overlays sidebar content */}
            {userMenuOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setUserMenuOpen(false)}
                />
                <div className="absolute bottom-full left-0 right-0 z-50 mx-2 mb-1 rounded-xl bg-primary-900/95 backdrop-blur-md border border-primary-700 shadow-lg animate-in">
                  <div className="px-3 py-3 space-y-3">
                    {/* Connections */}
                    <div>
                      <p className="px-3 text-[10px] font-semibold uppercase tracking-wider text-primary-400 mb-2">
                        Connections
                      </p>
                      <div className="flex gap-2 px-3">
                        <Link
                          href="/analytics"
                          onClick={() => setUserMenuOpen(false)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-800 border border-primary-700 text-xs font-medium text-cream-200 hover:bg-primary-700 transition-colors"
                        >
                          <Globe className="h-3.5 w-3.5 text-primary-400" />
                          GSC
                        </Link>
                        <Link
                          href="/settings"
                          onClick={() => setUserMenuOpen(false)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-800 border border-primary-700 text-xs font-medium text-cream-200 hover:bg-primary-700 transition-colors"
                        >
                          <Globe className="h-3.5 w-3.5 text-primary-400" />
                          WordPress
                        </Link>
                      </div>
                    </div>

                    {/* Credits */}
                    <Link
                      href="/settings/billing"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-cream-300 hover:bg-primary-800 hover:text-cream-100 transition-colors"
                    >
                      <Zap className="h-4 w-4 text-amber-500" />
                      <span>Credits</span>
                      <span className="ml-auto text-sm font-medium text-amber-500">
                        {user?.subscription_tier === "free" ? "Free" : "Pro"}
                      </span>
                    </Link>

                    {/* Settings */}
                    <Link
                      href="/settings"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-cream-300 hover:bg-primary-800 hover:text-cream-100 transition-colors"
                    >
                      <Settings className="h-4 w-4" />
                      Settings
                    </Link>

                    {/* Admin section */}
                    {isAdmin && (
                      <div>
                        <p className="px-3 text-[10px] font-semibold uppercase tracking-wider text-amber-500 mb-2">
                          Admin
                        </p>
                        <div className="space-y-0.5">
                          <Link
                            href="/admin"
                            onClick={() => setUserMenuOpen(false)}
                            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-cream-300 hover:bg-primary-800 hover:text-cream-100 transition-colors"
                          >
                            <LayoutDashboard className="h-4 w-4" />
                            Dashboard
                          </Link>
                          <Link
                            href="/admin/users"
                            onClick={() => setUserMenuOpen(false)}
                            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-cream-300 hover:bg-primary-800 hover:text-cream-100 transition-colors"
                          >
                            <Users className="h-4 w-4" />
                            User Management
                          </Link>
                          <Link
                            href="/admin/audit-logs"
                            onClick={() => setUserMenuOpen(false)}
                            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-cream-300 hover:bg-primary-800 hover:text-cream-100 transition-colors"
                          >
                            <FileSearch className="h-4 w-4" />
                            System Logs
                          </Link>
                        </div>
                      </div>
                    )}

                    {/* Sign Out */}
                    <button
                      onClick={handleSignOut}
                      className="flex w-full items-center gap-3 px-3 py-2 rounded-lg text-sm text-cream-300 hover:bg-primary-800 hover:text-cream-100 transition-colors"
                    >
                      <LogOut className="h-4 w-4" />
                      Sign Out
                    </button>
                  </div>
                </div>
              </>
            )}

            {/* User card - always visible at bottom */}
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="w-full flex items-center gap-3 p-4 hover:bg-primary-900 transition-colors"
            >
              <div className="h-9 w-9 rounded-full bg-primary-700 flex items-center justify-center shrink-0">
                <span className="text-sm font-medium text-cream-100">{userInitials}</span>
              </div>
              <div className="flex-1 min-w-0 text-left">
                <p className="text-sm font-medium text-cream-100 truncate">
                  {user?.name || "Loading..."}
                </p>
                <p className="text-xs text-primary-400 truncate">
                  {user?.email || ""}
                </p>
              </div>
              {userMenuOpen ? (
                <ChevronDown className="h-4 w-4 text-primary-400 shrink-0" />
              ) : (
                <ChevronUp className="h-4 w-4 text-primary-400 shrink-0" />
              )}
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top header */}
        <header className="sticky top-0 z-30 h-16 bg-surface/80 backdrop-blur-md border-b border-surface-tertiary">
          <div className="flex h-full items-center justify-between px-4 lg:px-8">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg hover:bg-surface-secondary"
            >
              <Menu className="h-5 w-5 text-text-secondary" />
            </button>

            <div className="flex-1" />

            {/* Top-right user avatar (mobile/quick access) */}
            <div className="relative">
              <button
                onClick={() => router.push("/settings")}
                className="flex items-center gap-2 p-2 rounded-xl hover:bg-surface-secondary transition-colors"
              >
                <div className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center">
                  <span className="text-sm font-medium text-primary-700">{userInitials}</span>
                </div>
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 lg:p-8">{children}</main>
      </div>
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <TeamProvider>
      <DashboardContent>{children}</DashboardContent>
    </TeamProvider>
  );
}
