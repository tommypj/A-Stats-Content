"use client";

import { SocialAccount, SocialPlatform } from "@/lib/api";
import { Twitter, Linkedin, Facebook, Instagram, CheckCircle } from "lucide-react";
import { Card } from "@/components/ui/card";

interface PlatformSelectorProps {
  accounts: SocialAccount[];
  selectedAccountIds: string[];
  onSelectionChange: (accountIds: string[]) => void;
  content: string;
}

const PLATFORM_LIMITS = {
  twitter: 280,
  linkedin: 3000,
  facebook: 63206,
  instagram: 2200,
};

export function PlatformSelector({
  accounts,
  selectedAccountIds,
  onSelectionChange,
  content,
}: PlatformSelectorProps) {
  const contentLength = content.length;

  const handleToggle = (accountId: string) => {
    if (selectedAccountIds.includes(accountId)) {
      onSelectionChange(selectedAccountIds.filter((id) => id !== accountId));
    } else {
      onSelectionChange([...selectedAccountIds, accountId]);
    }
  };

  const getPlatformIcon = (platform: SocialPlatform) => {
    switch (platform) {
      case "twitter":
        return <Twitter className="h-5 w-5" />;
      case "linkedin":
        return <Linkedin className="h-5 w-5" />;
      case "facebook":
        return <Facebook className="h-5 w-5" />;
      case "instagram":
        return <Instagram className="h-5 w-5" />;
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

  const getCharacterLimitStatus = (platform: SocialPlatform) => {
    const limit = PLATFORM_LIMITS[platform];
    const percentage = (contentLength / limit) * 100;

    if (contentLength > limit) {
      return {
        color: "text-red-500",
        bgColor: "bg-red-500/10",
        status: "exceeds",
      };
    } else if (percentage >= 90) {
      return {
        color: "text-yellow-600",
        bgColor: "bg-yellow-500/10",
        status: "warning",
      };
    } else {
      return {
        color: "text-green-600",
        bgColor: "bg-green-500/10",
        status: "ok",
      };
    }
  };

  if (accounts.length === 0) {
    return (
      <Card className="p-6 text-center">
        <p className="text-text-secondary mb-4">
          No social accounts connected yet.
        </p>
        <a
          href="/social/accounts"
          className="text-primary-500 hover:text-primary-600 font-medium"
        >
          Connect an account to get started
        </a>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-text-primary">
        Select Platforms ({selectedAccountIds.length})
      </h3>
      <div className="space-y-2">
        {accounts.map((account) => {
          const isSelected = selectedAccountIds.includes(account.id);
          const limitStatus = getCharacterLimitStatus(account.platform);
          const limit = PLATFORM_LIMITS[account.platform];

          return (
            <button
              key={account.id}
              type="button"
              onClick={() => handleToggle(account.id)}
              className={`w-full p-4 border rounded-xl transition-all ${
                isSelected
                  ? "border-primary-500 bg-primary-500/5"
                  : "border-surface-tertiary hover:bg-surface-secondary"
              } ${!account.is_connected ? "opacity-50 cursor-not-allowed" : ""}`}
              disabled={!account.is_connected}
            >
              <div className="flex items-center gap-3">
                {/* Checkbox */}
                <div
                  className={`h-5 w-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                    isSelected
                      ? "border-primary-500 bg-primary-500"
                      : "border-surface-tertiary"
                  }`}
                >
                  {isSelected && <CheckCircle className="h-4 w-4 text-white" />}
                </div>

                {/* Platform Icon */}
                <div
                  className={`${getPlatformColor(account.platform)} p-2 rounded-lg text-white flex-shrink-0`}
                >
                  {getPlatformIcon(account.platform)}
                </div>

                {/* Account Info */}
                <div className="flex-1 text-left min-w-0">
                  <p className="font-medium text-text-primary truncate">
                    {account.display_name}
                  </p>
                  <p className="text-sm text-text-secondary truncate">
                    @{account.username}
                  </p>
                </div>

                {/* Character Counter */}
                {contentLength > 0 && (
                  <div className="flex-shrink-0">
                    <div
                      className={`px-2 py-1 rounded text-xs font-medium ${limitStatus.bgColor} ${limitStatus.color}`}
                    >
                      {contentLength} / {limit}
                    </div>
                    {limitStatus.status === "exceeds" && (
                      <p className="text-xs text-red-500 mt-1">Too long</p>
                    )}
                    {limitStatus.status === "warning" && (
                      <p className="text-xs text-yellow-600 mt-1">Near limit</p>
                    )}
                  </div>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Warning if any platform exceeds limit */}
      {selectedAccountIds.some((id) => {
        const account = accounts.find((a) => a.id === id);
        if (!account) return false;
        return contentLength > PLATFORM_LIMITS[account.platform];
      }) && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
          <p className="text-sm text-red-600">
            Your content exceeds the character limit for some platforms. It will be
            truncated when posted.
          </p>
        </div>
      )}
    </div>
  );
}
