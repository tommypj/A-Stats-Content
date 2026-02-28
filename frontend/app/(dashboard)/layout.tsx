"use client";

import { useState, useEffect, useRef, useCallback } from "react";
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
  Search,
  TrendingUp,
  Lightbulb,
  Activity,
  FolderOpen,
  MessageSquare,
  Bell,
  CheckCircle2,
  XCircle,
  Keyboard,
  Layers,
  DollarSign,
  Building2,
} from "lucide-react";
import { clsx } from "clsx";
import { toast } from "sonner";
import { ProjectProvider, useProject } from "@/contexts/ProjectContext";
import { ProjectSwitcher } from "@/components/project/project-switcher";
import { api, UserResponse, GenerationNotification } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { KeyboardShortcutsDialog } from "@/components/ui/keyboard-shortcuts-dialog";
import { ErrorBoundary } from "@/components/ui/error-boundary";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Outlines", href: "/outlines", icon: FileText },
  { name: "Articles", href: "/articles", icon: Sparkles },
  { name: "Content Calendar", href: "/content-calendar", icon: Calendar },
  { name: "Keyword Research", href: "/keyword-research", icon: Search },
  { name: "Images", href: "/images", icon: ImageIcon },
  { name: "Bulk Content", href: "/bulk", icon: Layers },
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
  {
    name: "Analytics",
    icon: BarChart3,
    submenu: [
      { name: "Overview", href: "/analytics", icon: LayoutDashboard },
      { name: "Keywords", href: "/analytics/keywords", icon: Search },
      { name: "Pages", href: "/analytics/pages", icon: FileText },
      { name: "Article Performance", href: "/analytics/articles", icon: TrendingUp },
      { name: "Content Opportunities", href: "/analytics/opportunities", icon: Lightbulb },
      { name: "Content Health", href: "/analytics/content-health", icon: Activity },
      { name: "AEO Scores", href: "/analytics/aeo", icon: Zap },
      { name: "Revenue", href: "/analytics/revenue", icon: DollarSign },
    ],
  },
  { name: "Knowledge", href: "/knowledge", icon: BookOpen },
  {
    name: "Projects",
    icon: FolderOpen,
    submenu: [
      { name: "All Projects", href: "/projects", icon: FolderOpen },
      { name: "Brand Voice", href: "/projects/brand-voice", icon: MessageSquare },
    ],
  },
  {
    name: "Agency",
    icon: Building2,
    submenu: [
      { name: "Dashboard", href: "/agency", icon: LayoutDashboard },
      { name: "Clients", href: "/agency/clients", icon: Users },
      { name: "Reports", href: "/agency/reports", icon: FileText },
      { name: "Branding", href: "/agency/branding", icon: Globe },
    ],
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const SEEN_KEY = "notification_seen_ids";

function getSeenIds(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = localStorage.getItem(SEEN_KEY);
    return raw ? new Set(JSON.parse(raw) as string[]) : new Set();
  } catch {
    return new Set();
  }
}

function saveSeenIds(ids: Set<string>): void {
  if (typeof window === "undefined") return;
  // Keep at most 200 IDs to avoid unbounded growth
  const trimmed = Array.from(ids).slice(-200);
  localStorage.setItem(SEEN_KEY, JSON.stringify(trimmed));
}

function getResourceHref(n: GenerationNotification): string {
  if (n.type === "article") return `/articles/${n.resource_id}`;
  if (n.type === "outline") return `/outlines/${n.resource_id}`;
  return "/images";
}

function formatRelativeTime(isoTimestamp: string): string {
  const diff = Date.now() - new Date(isoTimestamp).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

function typeLabel(type: GenerationNotification["type"]): string {
  if (type === "article") return "Article";
  if (type === "outline") return "Outline";
  return "Image";
}

// ---------------------------------------------------------------------------
// NotificationBell component
// ---------------------------------------------------------------------------

function NotificationBell() {
  const router = useRouter();
  const [notifications, setNotifications] = useState<GenerationNotification[]>([]);
  const [seenIds, setSeenIds] = useState<Set<string>>(new Set());
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Load seen IDs from localStorage on mount
  useEffect(() => {
    setSeenIds(getSeenIds());
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const fetchNotifications = useCallback(async () => {
    try {
      const data = await api.notifications.generationStatus();
      setNotifications(data.notifications);
    } catch {
      // Silent fail — polling is best-effort
    }
  }, []);

  // Initial fetch + 30-second polling interval (pauses when tab is hidden)
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(() => {
      if (document.visibilityState === "visible") {
        fetchNotifications();
      }
    }, 30_000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  const unseenCount = notifications.filter((n) => !seenIds.has(n.id)).length;

  function handleOpen() {
    setOpen((prev) => !prev);
    if (!open) {
      // Mark all current notifications as seen when opening
      const newSeen = new Set(seenIds);
      notifications.forEach((n) => newSeen.add(n.id));
      setSeenIds(newSeen);
      saveSeenIds(newSeen);
    }
  }

  function handleNotificationClick(n: GenerationNotification) {
    // FE-AUTH-28: close dropdown before navigating so it doesn't stay open on new page
    setOpen(false);
    router.push(getResourceHref(n));
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={handleOpen}
        aria-label="Notifications"
        aria-expanded={open}
        className="relative flex items-center justify-center h-9 w-9 rounded-xl hover:bg-surface-secondary transition-colors"
      >
        <Bell className="h-5 w-5 text-text-secondary" />
        {unseenCount > 0 && (
          <span className="absolute top-1 right-1 h-2.5 w-2.5 rounded-full bg-red-500 border-2 border-white" />
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 rounded-xl bg-white border border-surface-tertiary shadow-lg z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-surface-tertiary">
            <span className="text-sm font-semibold text-text-primary">Recent Generations</span>
            {notifications.length > 0 && (
              <span className="text-xs text-text-secondary">
                {notifications.length} item{notifications.length === 1 ? "" : "s"}
              </span>
            )}
          </div>

          {/* Notification list */}
          {notifications.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <Bell className="h-8 w-8 text-surface-tertiary mx-auto mb-2" />
              <p className="text-sm text-text-secondary">No recent completions</p>
              <p className="text-xs text-text-tertiary mt-1">
                Notifications appear when generation finishes
              </p>
            </div>
          ) : (
            <ul className="max-h-72 overflow-y-auto divide-y divide-surface-tertiary">
              {notifications.map((n) => (
                <li key={n.id}>
                  <button
                    onClick={() => handleNotificationClick(n)}
                    className="w-full flex items-start gap-3 px-4 py-3 hover:bg-surface-secondary transition-colors text-left"
                  >
                    {/* Status icon */}
                    {n.status === "completed" ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                    )}

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-text-secondary uppercase tracking-wide">
                        {typeLabel(n.type)} {n.status}
                      </p>
                      <p className="text-sm text-text-primary truncate mt-0.5">{n.title}</p>
                      <p className="text-xs text-text-tertiary mt-0.5">
                        {formatRelativeTime(n.timestamp)}
                      </p>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main layout
// ---------------------------------------------------------------------------

function DashboardContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { currentProject } = useProject();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [expandedMenus, setExpandedMenus] = useState<Set<string>>(() => {
    // Only auto-expand the submenu that contains the current active page
    const initial = new Set<string>();
    for (const item of navigation) {
      if ("submenu" in item && item.submenu?.some((sub) => pathname.startsWith(sub.href))) {
        initial.add(item.name);
      }
    }
    return initial;
  });
  const [user, setUser] = useState<UserResponse | null>(null);
  const [showShortcutsDialog, setShowShortcutsDialog] = useState(false);

  useKeyboardShortcuts([
    {
      key: "/",
      ctrl: true,
      handler: () => setShowShortcutsDialog(true),
    },
    {
      key: "?",
      handler: () => setShowShortcutsDialog(true),
    },
  ]);

  useEffect(() => {
    const loadUser = async () => {
      try {
        const data = await api.auth.me();
        setUser(data);
      } catch {
        // Failed to load user — cookie is likely invalid/expired.
        // No localStorage tokens to clear; cookies are managed by the browser/backend.
        // Redirect to login.
        router.push("/login");
      }
    };
    loadUser();
  }, [router]);

  const handleSignOut = async () => {
    try {
      await api.auth.logout();
      useAuthStore.getState().logout();
      router.push("/login");
    } catch {
      toast.error("Failed to sign out. Please try again.");
    }
  };

  const isAdmin = user?.role === "admin" || user?.role === "super_admin";
  const userInitials = user?.name
    ? user.name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : "U";

  return (
    <div className="min-h-screen bg-surface-secondary">
      {/* Skip to main content — visible on keyboard focus only */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary-600 focus:text-white focus:rounded-lg focus:outline-none"
      >
        Skip to main content
      </a>

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
            {isAdmin && (
              <div className="h-8 w-8 rounded-lg bg-amber-600/20 border border-amber-600/40 flex items-center justify-center">
                <Shield className="h-4 w-4 text-amber-500" />
              </div>
            )}
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1 rounded-lg hover:bg-primary-800"
            >
              <X className="h-5 w-5 text-cream-300" />
            </button>
          </div>

          {/* Project Switcher */}
          <div className="px-3 py-4 border-b border-primary-800">
            <ProjectSwitcher />
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto scrollbar-sidebar">
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
                      aria-expanded={isExpanded}
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
                              onClick={() => setSidebarOpen(false)}
                              className={clsx(
                                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
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
                  onClick={() => setSidebarOpen(false)}
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
                <div className="absolute bottom-full left-0 right-0 z-50 mx-2 mb-1 rounded-xl bg-primary-900/95 backdrop-blur-md border border-primary-700 shadow-lg animate-in max-h-[70vh] overflow-y-auto">
                  <div className="px-3 py-3 space-y-3">
                    {/* Connections */}
                    <div>
                      <p className="px-3 text-[10px] font-semibold uppercase tracking-wider text-primary-400 mb-2">
                        Project Integrations
                      </p>
                      <div className="flex gap-2 px-3">
                        <Link
                          href={
                            currentProject
                              ? `/projects/${currentProject.id}/settings`
                              : "/projects"
                          }
                          onClick={() => setUserMenuOpen(false)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-800 border border-primary-700 text-xs font-medium text-cream-200 hover:bg-primary-700 transition-colors"
                        >
                          <Globe className="h-3.5 w-3.5 text-primary-400" />
                          GSC
                        </Link>
                        <Link
                          href={
                            currentProject
                              ? `/projects/${currentProject.id}/settings`
                              : "/projects"
                          }
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
              aria-expanded={userMenuOpen}
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
                <ChevronUp className="h-4 w-4 text-primary-400 shrink-0" />
              ) : (
                <ChevronDown className="h-4 w-4 text-primary-400 shrink-0" />
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
              aria-expanded={sidebarOpen}
              aria-label="Open sidebar"
              className="lg:hidden p-2.5 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-surface-secondary"
            >
              <Menu className="h-5 w-5 text-text-secondary" />
            </button>

            <div className="flex-1" />

            {/* Top-right actions: keyboard shortcuts + notification bell + user avatar */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowShortcutsDialog(true)}
                title="Keyboard shortcuts (Ctrl+/)"
                aria-label="Show keyboard shortcuts"
                className="p-2 rounded-xl text-text-muted hover:bg-surface-secondary hover:text-text-primary transition-colors"
              >
                <Keyboard className="h-5 w-5" />
              </button>
              <NotificationBell />

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
        <main id="main-content" className="p-4 lg:p-8 overflow-x-hidden">
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </div>

      {/* Global keyboard shortcuts dialog */}
      <KeyboardShortcutsDialog
        isOpen={showShortcutsDialog}
        onClose={() => setShowShortcutsDialog(false)}
      />
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  // Use Zustand persisted state — avoids flash of "unauthenticated" on page refresh.
  const { isAuthenticated: zustandAuthenticated, isLoading: zustandLoading, logout } = useAuthStore();
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    if (zustandLoading) return; // Wait for Zustand hydration to complete
    if (!zustandAuthenticated) {
      router.push("/login");
      return;
    }
    // AUTH-16: Verify session against the backend before rendering protected content.
    // Catches stale localStorage state (expired cookies) without requiring a full logout.
    api.auth.me().then(() => {
      setIsAuthenticated(true);
    }).catch(() => {
      logout();
      router.push("/login");
    });
  }, [zustandAuthenticated, zustandLoading, router, logout]);

  // Safety timeout: if Zustand hydration never completes (edge case), redirect
  // to login after 10 seconds to avoid an infinite loading state.
  useEffect(() => {
    const timeout = setTimeout(() => {
      setIsAuthenticated((prev) => {
        if (!prev) {
          router.push("/login");
        }
        return prev;
      });
    }, 10000);
    return () => clearTimeout(timeout);
  }, [router]);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-secondary">
        <div className="h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <ProjectProvider>
      <DashboardContent>{children}</DashboardContent>
    </ProjectProvider>
  );
}
