"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { api, SocialAccount, SocialPost } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Twitter,
  Linkedin,
  Facebook,
  Instagram,
  PenSquare,
  Calendar,
  CheckCircle,
  TrendingUp,
  AlertCircle,
} from "lucide-react";

export default function SocialDashboard() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [upcomingPosts, setUpcomingPosts] = useState<SocialPost[]>([]);
  const [stats, setStats] = useState({
    scheduled: 0,
    postedThisWeek: 0,
    totalEngagement: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [accountsRes, upcomingRes, recentRes] = await Promise.all([
        api.social.accounts(),
        api.social.posts({ page: 1, page_size: 5 }),
        api.social.posts({ page: 1, page_size: 20, status: "posted" }),
      ]);

      setAccounts(accountsRes.accounts);
      // Show upcoming (non-posted) posts
      const upcoming = upcomingRes.items.filter(
        (p) => p.status !== "posted" && p.status !== "failed" && p.status !== "cancelled"
      );
      setUpcomingPosts(upcoming);

      // Calculate stats from separate queries
      const scheduled = upcoming.length;
      const postedThisWeek = recentRes.items.filter(
        (p) => isThisWeek(p.published_at || p.updated_at || "")
      ).length;

      setStats({
        scheduled,
        postedThisWeek,
        totalEngagement: 0, // Would need analytics endpoint
      });
    } catch (error) {
      toast.error("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  const isThisWeek = (date: string) => {
    const postDate = new Date(date);
    const now = new Date();
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    return postDate >= weekAgo && postDate <= now;
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case "twitter":
        return <Twitter className="h-5 w-5" />;
      case "linkedin":
        return <Linkedin className="h-5 w-5" />;
      case "facebook":
        return <Facebook className="h-5 w-5" />;
      case "instagram":
        return <Instagram className="h-5 w-5" />;
      default:
        return null;
    }
  };

  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case "twitter":
        return "text-blue-500";
      case "linkedin":
        return "text-blue-700";
      case "facebook":
        return "text-blue-600";
      case "instagram":
        return "text-pink-500";
      default:
        return "text-gray-500";
    }
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-10 bg-surface-secondary rounded w-1/3" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-surface-secondary rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Social Media</h1>
          <p className="text-text-secondary mt-1">
            Manage your social media presence across platforms
          </p>
        </div>
        <Button
          onClick={() => router.push("/social/compose")}
          leftIcon={<PenSquare className="h-4 w-4" />}
        >
          Create Post
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary">Scheduled Posts</p>
              <p className="text-3xl font-bold text-text-primary mt-1">
                {stats.scheduled}
              </p>
            </div>
            <div className="h-12 w-12 bg-primary-500/10 rounded-xl flex items-center justify-center">
              <Calendar className="h-6 w-6 text-primary-500" />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary">Posted This Week</p>
              <p className="text-3xl font-bold text-text-primary mt-1">
                {stats.postedThisWeek}
              </p>
            </div>
            <div className="h-12 w-12 bg-green-500/10 rounded-xl flex items-center justify-center">
              <CheckCircle className="h-6 w-6 text-green-500" />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary">Connected Accounts</p>
              <p className="text-3xl font-bold text-text-primary mt-1">
                {accounts.filter((a) => a.is_connected).length}
              </p>
            </div>
            <div className="h-12 w-12 bg-blue-500/10 rounded-xl flex items-center justify-center">
              <TrendingUp className="h-6 w-6 text-blue-500" />
            </div>
          </div>
        </Card>
      </div>

      {/* Connected Accounts */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-text-primary">
            Connected Accounts
          </h2>
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push("/social/accounts")}
          >
            Manage Accounts
          </Button>
        </div>

        {accounts.length === 0 ? (
          <div className="text-center py-8">
            <AlertCircle className="h-12 w-12 text-text-tertiary mx-auto mb-4" />
            <p className="text-text-secondary mb-4">
              No social accounts connected yet
            </p>
            <Button onClick={() => router.push("/social/accounts")}>
              Connect Your First Account
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {accounts.map((account) => (
              <div
                key={account.id}
                className="p-4 border border-surface-tertiary rounded-xl hover:bg-surface-secondary transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className={getPlatformColor(account.platform)}>
                    {getPlatformIcon(account.platform)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-text-primary truncate">
                      {account.display_name}
                    </p>
                    <p className="text-sm text-text-secondary truncate">
                      @{account.username}
                    </p>
                  </div>
                </div>
                {account.is_connected ? (
                  <div className="mt-3 flex items-center gap-1 text-xs text-green-600">
                    <CheckCircle className="h-3 w-3" />
                    Connected
                  </div>
                ) : (
                  <div className="mt-3 flex items-center gap-1 text-xs text-red-600">
                    <AlertCircle className="h-3 w-3" />
                    Disconnected
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Upcoming Posts */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-text-primary">
            Upcoming Posts
          </h2>
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push("/social/calendar")}
          >
            View Calendar
          </Button>
        </div>

        {upcomingPosts.length === 0 ? (
          <div className="text-center py-8">
            <Calendar className="h-12 w-12 text-text-tertiary mx-auto mb-4" />
            <p className="text-text-secondary mb-4">No scheduled posts</p>
            <Button onClick={() => router.push("/social/compose")}>
              Schedule Your First Post
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {upcomingPosts.slice(0, 5).map((post) => (
              <div
                key={post.id}
                className="p-4 border border-surface-tertiary rounded-xl hover:bg-surface-secondary transition-colors cursor-pointer"
                onClick={() => router.push(`/social/calendar`)}
              >
                <div className="flex items-start gap-4">
                  <div className="flex-1">
                    <p className="text-text-primary line-clamp-2 mb-2">
                      {post.content}
                    </p>
                    <div className="flex items-center gap-4 text-sm text-text-secondary">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        {formatDate(post.scheduled_at)}
                      </span>
                      <div className="flex items-center gap-2">
                        {post.platforms.map((platform) => (
                          <span
                            key={platform}
                            className={getPlatformColor(platform)}
                          >
                            {getPlatformIcon(platform)}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Button
          variant="outline"
          className="h-auto py-6 flex flex-col gap-2"
          onClick={() => router.push("/social/compose")}
        >
          <PenSquare className="h-6 w-6" />
          <span>Compose Post</span>
        </Button>
        <Button
          variant="outline"
          className="h-auto py-6 flex flex-col gap-2"
          onClick={() => router.push("/social/calendar")}
        >
          <Calendar className="h-6 w-6" />
          <span>View Calendar</span>
        </Button>
        <Button
          variant="outline"
          className="h-auto py-6 flex flex-col gap-2"
          onClick={() => router.push("/social/history")}
        >
          <TrendingUp className="h-6 w-6" />
          <span>Post History</span>
        </Button>
      </div>
    </div>
  );
}
