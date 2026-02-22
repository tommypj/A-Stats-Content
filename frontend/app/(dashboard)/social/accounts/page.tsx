"use client";

import { useEffect, useState } from "react";
import { api, SocialAccount, SocialPlatform } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Twitter,
  Linkedin,
  Facebook,
  Instagram,
  CheckCircle,
  AlertCircle,
  Trash2,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { parseApiError } from "@/lib/api";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [connectingPlatform, setConnectingPlatform] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.social.accounts();
      setAccounts(res.accounts);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async (platform: SocialPlatform) => {
    try {
      setConnectingPlatform(platform);
      setError(null);

      const res = await api.social.getConnectUrl(platform);
      window.location.href = res.authorization_url;
    } catch (err) {
      setError(parseApiError(err).message);
      setConnectingPlatform(null);
    }
  };

  const handleDisconnect = async (accountId: string, platform: string) => {
    if (!confirm(`Are you sure you want to disconnect this ${platform} account?`)) {
      return;
    }

    try {
      setError(null);
      await api.social.disconnectAccount(accountId);
      await loadAccounts();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const handleVerify = async (accountId: string) => {
    try {
      setError(null);
      await api.social.verify(accountId);
      await loadAccounts();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const getPlatformIcon = (platform: SocialPlatform, className = "h-6 w-6") => {
    switch (platform) {
      case "twitter":
        return <Twitter className={className} />;
      case "linkedin":
        return <Linkedin className={className} />;
      case "facebook":
        return <Facebook className={className} />;
      case "instagram":
        return <Instagram className={className} />;
    }
  };

  const getPlatformColor = (platform: SocialPlatform) => {
    switch (platform) {
      case "twitter":
        return "bg-blue-500";
      case "linkedin":
        return "bg-blue-700";
      case "facebook":
        return "bg-blue-600";
      case "instagram":
        return "bg-gradient-to-br from-purple-500 to-pink-500";
    }
  };

  const getPlatformName = (platform: SocialPlatform) => {
    return platform.charAt(0).toUpperCase() + platform.slice(1);
  };

  const availablePlatforms: SocialPlatform[] = ["twitter", "linkedin", "facebook", "instagram"];

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-10 bg-surface-secondary rounded w-1/3" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-48 bg-surface-secondary rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-text-primary">Social Accounts</h1>
        <p className="text-text-secondary mt-1">
          Connect and manage your social media accounts
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-red-500 font-medium">Error</p>
            <p className="text-red-400 text-sm mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Connected Accounts */}
      <div>
        <h2 className="text-xl font-semibold text-text-primary mb-4">
          Connected Accounts ({accounts.length})
        </h2>
        {accounts.length === 0 ? (
          <Card className="p-8 text-center">
            <p className="text-text-secondary">
              No accounts connected yet. Connect your first account below.
            </p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {accounts.map((account) => (
              <Card key={account.id} className="p-6">
                <div className="flex items-start gap-4">
                  {/* Platform Icon */}
                  <div
                    className={`${getPlatformColor(account.platform)} p-3 rounded-xl text-white flex-shrink-0`}
                  >
                    {getPlatformIcon(account.platform)}
                  </div>

                  {/* Account Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-text-primary truncate">
                          {account.display_name}
                        </h3>
                        <p className="text-sm text-text-secondary truncate">
                          @{account.username}
                        </p>
                      </div>
                      {account.is_connected ? (
                        <span className="flex items-center gap-1 text-xs text-green-600 whitespace-nowrap">
                          <CheckCircle className="h-3 w-3" />
                          Active
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-xs text-red-600 whitespace-nowrap">
                          <AlertCircle className="h-3 w-3" />
                          Disconnected
                        </span>
                      )}
                    </div>

                    <div className="mt-3 text-xs text-text-tertiary">
                      <p>
                        Connected{" "}
                        {new Date(account.connected_at).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </p>
                    </div>

                    {account.last_error && (
                      <div className="mt-3 p-2 bg-red-500/10 rounded text-xs text-red-600">
                        {account.last_error}
                      </div>
                    )}

                    {/* Actions */}
                    <div className="mt-4 flex items-center gap-2">
                      {!account.is_connected && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleVerify(account.id)}
                          leftIcon={<RefreshCw className="h-3 w-3" />}
                        >
                          Reconnect
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() =>
                          handleDisconnect(account.id, getPlatformName(account.platform))
                        }
                        leftIcon={<Trash2 className="h-3 w-3" />}
                      >
                        Disconnect
                      </Button>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Connect New Account */}
      <div>
        <h2 className="text-xl font-semibold text-text-primary mb-4">
          Connect New Account
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {availablePlatforms.map((platform) => {
            const isConnected = accounts.some((a) => a.platform === platform);
            return (
              <Card
                key={platform}
                className="p-6 hover:bg-surface-secondary transition-colors"
              >
                <div className="flex flex-col items-center text-center gap-4">
                  <div
                    className={`${getPlatformColor(platform)} p-4 rounded-xl text-white`}
                  >
                    {getPlatformIcon(platform, "h-8 w-8")}
                  </div>
                  <div>
                    <h3 className="font-semibold text-text-primary">
                      {getPlatformName(platform)}
                    </h3>
                    <p className="text-xs text-text-secondary mt-1">
                      {isConnected ? "Already connected" : "Not connected"}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant={isConnected ? "outline" : "primary"}
                    onClick={() => handleConnect(platform)}
                    isLoading={connectingPlatform === platform}
                    leftIcon={<ExternalLink className="h-3 w-3" />}
                    className="w-full"
                  >
                    {isConnected ? "Add Another" : "Connect"}
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Help Text */}
      <Card className="p-6 bg-blue-500/5 border-blue-500/20">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-text-primary">About Social Connections</h3>
            <p className="text-sm text-text-secondary mt-2">
              You can connect multiple accounts for each platform. When creating a post,
              you'll be able to choose which accounts to publish to.
            </p>
            <ul className="mt-3 space-y-1 text-sm text-text-secondary list-disc list-inside">
              <li>Twitter: Requires Twitter Developer account</li>
              <li>LinkedIn: Supports personal and company pages</li>
              <li>Facebook: Can connect pages and groups</li>
              <li>Instagram: Business accounts only (via Facebook)</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}
