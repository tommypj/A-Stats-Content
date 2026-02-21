"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  Sparkles,
  Image as ImageIcon,
  BarChart3,
  Settings,
  HelpCircle,
  Menu,
  X,
  LogOut,
  ChevronDown,
  Share2,
  Calendar,
  History,
  Edit3,
  Users,
  BookOpen,
} from "lucide-react";
import { clsx } from "clsx";
import { TeamProvider } from "@/contexts/TeamContext";
import { TeamSwitcher } from "@/components/team/team-switcher";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Outlines", href: "/outlines", icon: FileText },
  { name: "Articles", href: "/articles", icon: Sparkles },
  { name: "Images", href: "/images", icon: ImageIcon },
  {
    name: "Social",
    icon: Share2,
    submenu: [
      { name: "Dashboard", href: "/social/dashboard", icon: LayoutDashboard },
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

const secondaryNavigation = [
  { name: "Settings", href: "/settings", icon: Settings },
  { name: "Help & Support", href: "/help", icon: HelpCircle },
];

function DashboardContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [expandedMenus, setExpandedMenus] = useState<Set<string>>(new Set(["Social"]));

  return (
    <div className="min-h-screen bg-surface-secondary">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-surface-tertiary transform transition-transform duration-200 ease-in-out lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex h-16 items-center justify-between px-4 border-b border-surface-tertiary">
            <Link href="/dashboard" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary-400 to-primary-600" />
              <span className="font-display text-lg font-semibold text-text-primary">
                A-Stats
              </span>
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1 rounded-lg hover:bg-surface-secondary"
            >
              <X className="h-5 w-5 text-text-secondary" />
            </button>
          </div>

          {/* Team Switcher */}
          <div className="px-3 py-4 border-b border-surface-tertiary">
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
                          ? "bg-primary-50 text-primary-600"
                          : "text-text-secondary hover:bg-surface-secondary hover:text-text-primary"
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
                      <div className="mt-1 ml-3 pl-3 border-l-2 border-surface-tertiary space-y-1">
                        {item.submenu?.map((subItem) => {
                          const isActive = pathname === subItem.href;
                          return (
                            <Link
                              key={subItem.name}
                              href={subItem.href}
                              className={clsx(
                                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                                isActive
                                  ? "bg-primary-50 text-primary-600"
                                  : "text-text-secondary hover:bg-surface-secondary hover:text-text-primary"
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
                      ? "bg-primary-50 text-primary-600"
                      : "text-text-secondary hover:bg-surface-secondary hover:text-text-primary"
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  {item.name}
                </Link>
              );
            })}

            <div className="pt-4 mt-4 border-t border-surface-tertiary">
              {secondaryNavigation.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={clsx(
                      "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                      isActive
                        ? "bg-primary-50 text-primary-600"
                        : "text-text-secondary hover:bg-surface-secondary hover:text-text-primary"
                    )}
                  >
                    <item.icon className="h-5 w-5" />
                    {item.name}
                  </Link>
                );
              })}
            </div>
          </nav>

          {/* User section */}
          <div className="p-4 border-t border-surface-tertiary">
            <div className="flex items-center gap-3 p-2 rounded-xl bg-surface-secondary">
              <div className="h-9 w-9 rounded-full bg-healing-lavender flex items-center justify-center">
                <span className="text-sm font-medium text-text-primary">U</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">
                  User Name
                </p>
                <p className="text-xs text-text-muted truncate">Free Plan</p>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top header */}
        <header className="sticky top-0 z-30 h-16 bg-white/80 backdrop-blur-md border-b border-surface-tertiary">
          <div className="flex h-full items-center justify-between px-4 lg:px-8">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg hover:bg-surface-secondary"
            >
              <Menu className="h-5 w-5 text-text-secondary" />
            </button>

            <div className="flex-1" />

            {/* User menu */}
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 p-2 rounded-xl hover:bg-surface-secondary transition-colors"
              >
                <div className="h-8 w-8 rounded-full bg-healing-lavender flex items-center justify-center">
                  <span className="text-sm font-medium text-text-primary">U</span>
                </div>
                <ChevronDown className="h-4 w-4 text-text-muted" />
              </button>

              {userMenuOpen && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setUserMenuOpen(false)}
                  />
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl border border-surface-tertiary shadow-lg z-50">
                    <div className="p-2">
                      <Link
                        href="/settings"
                        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-secondary hover:text-text-primary"
                        onClick={() => setUserMenuOpen(false)}
                      >
                        <Settings className="h-4 w-4" />
                        Settings
                      </Link>
                      <button className="flex w-full items-center gap-2 px-3 py-2 rounded-lg text-sm text-red-600 hover:bg-red-50">
                        <LogOut className="h-4 w-4" />
                        Sign Out
                      </button>
                    </div>
                  </div>
                </>
              )}
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
