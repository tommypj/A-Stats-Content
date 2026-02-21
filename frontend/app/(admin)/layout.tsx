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
  Activity,
  FileCheck,
  Image as ImageIcon,
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

  useEffect(() => {
    // Check if user is admin
    const checkAdminRole = async () => {
      try {
        const token = localStorage.getItem("auth_token");
        if (!token) {
          router.push("/login");
          return;
        }

        // Check user role via API
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
          <div className="h-8 w-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto" />
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
            <Link href="/admin" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-red-500 to-purple-600" />
              <div>
                <span className="font-display text-lg font-semibold text-text-primary">
                  A-Stats
                </span>
                <div className="flex items-center gap-1">
                  <Shield className="h-3 w-3 text-red-600" />
                  <span className="text-xs font-medium text-red-600">Admin</span>
                </div>
              </div>
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1 rounded-lg hover:bg-surface-secondary"
            >
              <X className="h-5 w-5 text-text-secondary" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => {
              // Item with submenu
              if ("submenu" in item) {
                const isExpanded = expandedMenus.has(item.name);
                const hasActiveChild = item.submenu.some((subItem) =>
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
                          ? "bg-purple-50 text-purple-600"
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
                        {item.submenu.map((subItem) => {
                          const isActive = pathname === subItem.href || pathname.startsWith(subItem.href + "/");
                          return (
                            <Link
                              key={subItem.name}
                              href={subItem.href}
                              className={clsx(
                                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                                isActive
                                  ? "bg-purple-50 text-purple-600"
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
                      ? "bg-purple-50 text-purple-600"
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
                        ? "bg-purple-50 text-purple-600"
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
            <Link
              href="/dashboard"
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-secondary hover:text-text-primary"
            >
              <LayoutDashboard className="h-4 w-4" />
              Back to Dashboard
            </Link>
            <div className="mt-2 flex items-center gap-3 p-2 rounded-xl bg-surface-secondary">
              <div className="h-9 w-9 rounded-full bg-red-100 flex items-center justify-center">
                <Shield className="h-5 w-5 text-red-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">
                  Admin User
                </p>
                <p className="text-xs text-text-muted truncate">Super Admin</p>
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
                <div className="h-8 w-8 rounded-full bg-red-100 flex items-center justify-center">
                  <Shield className="h-4 w-4 text-red-600" />
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
