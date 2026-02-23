"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  Users,
  BarChart3,
  Shield,
  Settings,
  Menu,
  X,
  LogOut,
  ChevronDown,
  FileSearch,
  FileCheck,
  Image as ImageIcon,
  Sparkles,
  Bell,
} from "lucide-react";
import { clsx } from "clsx";
import { api } from "@/lib/api";

const navigation = [
  { name: "Dashboard", href: "/admin", icon: LayoutDashboard },
  { name: "Users", href: "/admin/users", icon: Users },
  {
    name: "Content",
    icon: FileText,
    submenu: [
      { name: "Articles", href: "/admin/content/articles", icon: FileText },
      { name: "Outlines", href: "/admin/content/outlines", icon: FileCheck },
      { name: "Images", href: "/admin/content/images", icon: ImageIcon },
    ],
  },
  { name: "Analytics", href: "/admin/analytics", icon: BarChart3 },
  { name: "Audit Logs", href: "/admin/audit-logs", icon: FileSearch },
  { name: "Generations", href: "/admin/generations", icon: Sparkles },
  { name: "Alerts", href: "/admin/alerts", icon: Bell },
];

const secondaryNavigation = [
  { name: "Settings", href: "/admin/settings", icon: Settings },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [expandedMenus, setExpandedMenus] = useState<Set<string>>(new Set(["Content"]));
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [alertCount, setAlertCount] = useState(0);

  useEffect(() => {
    const fetchAlertCount = async () => {
      try {
        const data = await api.admin.alerts.count();
        setAlertCount(data.unread_count || 0);
      } catch {
        // Silently fail — alert count is non-critical
      }
    };
    if (isAdmin) {
      fetchAlertCount();
      const interval = setInterval(fetchAlertCount, 60000);
      return () => clearInterval(interval);
    }
  }, [isAdmin]);

  useEffect(() => {
    const checkAdminRole = async () => {
      try {
        const token = localStorage.getItem("auth_token");
        if (!token) {
          router.push("/login");
          return;
        }

        const user = await api.auth.me();
        if (user.role !== "admin" && user.role !== "super_admin") {
          router.push("/dashboard");
          return;
        }

        setIsAdmin(true);
        setLoading(false);
      } catch (error) {
        console.error("Failed to check admin role:", error);
        router.push("/login");
      }
    };

    checkAdminRole();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-secondary flex items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-text-secondary">Loading admin panel...</p>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return null;
  }

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
            <Link href="/admin" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-primary-700 flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-cream-200" />
              </div>
              <div>
                <span className="font-display text-lg font-semibold text-cream-100">
                  A-Stats
                </span>
                <div className="flex items-center gap-1">
                  <Shield className="h-3 w-3 text-amber-500" />
                  <span className="text-xs font-medium text-amber-500">Admin</span>
                </div>
              </div>
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1 rounded-lg hover:bg-primary-800"
            >
              <X className="h-5 w-5 text-cream-300" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => {
              // Item with submenu
              if ("submenu" in item) {
                const isExpanded = expandedMenus.has(item.name);
                const hasActiveChild = item.submenu?.some((subItem) =>
                  pathname === subItem.href || pathname.startsWith(subItem.href + "/")
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
                          const isActive = pathname === subItem.href || pathname.startsWith(subItem.href + "/");
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
                  <span className="flex-1">{item.name}</span>
                  {item.name === "Alerts" && alertCount > 0 && (
                    <span className="inline-flex items-center justify-center h-5 min-w-[20px] px-1.5 rounded-full bg-red-500 text-white text-xs font-bold">
                      {alertCount > 99 ? "99+" : alertCount}
                    </span>
                  )}
                </Link>
              );
            })}

            <div className="pt-4 mt-4 border-t border-primary-800">
              {secondaryNavigation.map((item) => {
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
            </div>
          </nav>

          {/* User section */}
          <div className="p-4 border-t border-primary-800">
            <Link
              href="/dashboard"
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-cream-300 hover:bg-primary-900 hover:text-cream-100"
            >
              <LayoutDashboard className="h-4 w-4" />
              Back to Dashboard
            </Link>
            <div className="mt-2 flex items-center gap-3 p-2 rounded-xl bg-primary-900">
              <div className="h-9 w-9 rounded-full bg-primary-700 flex items-center justify-center">
                <Shield className="h-5 w-5 text-amber-500" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-cream-100 truncate">
                  Admin User
                </p>
                <p className="text-xs text-primary-400 truncate">Super Admin</p>
              </div>
            </div>
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

            {/* User menu */}
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 p-2 rounded-xl hover:bg-surface-secondary transition-colors"
              >
                <div className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center">
                  <Shield className="h-4 w-4 text-primary-700" />
                </div>
                <ChevronDown className="h-4 w-4 text-text-muted" />
              </button>

              {userMenuOpen && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setUserMenuOpen(false)}
                  />
                  <div className="absolute right-0 mt-2 w-48 bg-surface rounded-xl border border-surface-tertiary shadow-soft-lg z-50">
                    <div className="p-2">
                      <Link
                        href="/admin/settings"
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
