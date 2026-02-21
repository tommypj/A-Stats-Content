"use client";

import { useState, useEffect } from "react";
import { Check, Globe, Loader2, X } from "lucide-react";
import { toast } from "sonner";

import { api, parseApiError, GSCSite } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface SiteSelectorProps {
  onSiteSelected?: () => void;
  onCancel?: () => void;
  showAsModal?: boolean;
}

export function SiteSelector({
  onSiteSelected,
  onCancel,
  showAsModal = false,
}: SiteSelectorProps) {
  const [sites, setSites] = useState<GSCSite[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedSite, setSelectedSite] = useState<string | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);

  useEffect(() => {
    loadSites();
  }, []);

  async function loadSites() {
    try {
      setIsLoading(true);
      const response = await api.analytics.sites();
      setSites(response.sites);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to load sites");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSelectSite(siteUrl: string) {
    try {
      setIsSelecting(true);
      setSelectedSite(siteUrl);
      await api.analytics.selectSite(siteUrl);
      toast.success("Site selected successfully!");
      onSiteSelected?.();
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to select site");
      setSelectedSite(null);
    } finally {
      setIsSelecting(false);
    }
  }

  const content = (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-display text-2xl font-bold text-text-primary">
            Select Your Site
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            Choose which Google Search Console property to track
          </p>
        </div>
        {showAsModal && onCancel && (
          <button
            onClick={onCancel}
            className="p-2 hover:bg-surface-secondary rounded-lg transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5 text-text-muted" />
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="py-12 flex flex-col items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500 mb-4" />
          <p className="text-sm text-text-secondary">Loading your sites...</p>
        </div>
      ) : sites.length === 0 ? (
        <div className="py-12 text-center">
          <Globe className="h-12 w-12 text-text-muted mx-auto mb-4" />
          <h3 className="font-semibold text-text-primary mb-2">No Sites Found</h3>
          <p className="text-sm text-text-secondary">
            No verified sites found in your Google Search Console account.
          </p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => window.open("https://search.google.com/search-console", "_blank")}
          >
            Open Google Search Console
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {sites.map((site) => (
            <button
              key={site.site_url}
              onClick={() => handleSelectSite(site.site_url)}
              disabled={isSelecting}
              className={cn(
                "w-full p-4 rounded-xl border-2 transition-all duration-200 text-left",
                "hover:border-primary-500 hover:bg-primary-50",
                "focus:outline-none focus:ring-2 focus:ring-primary-500",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                selectedSite === site.site_url
                  ? "border-primary-500 bg-primary-50"
                  : "border-surface-tertiary bg-white"
              )}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Globe className="h-4 w-4 text-text-muted flex-shrink-0" />
                    <span className="font-medium text-text-primary truncate">
                      {site.site_url}
                    </span>
                  </div>
                  <p className="text-xs text-text-muted">
                    Permission: {site.permission_level}
                  </p>
                </div>
                {selectedSite === site.site_url && isSelecting ? (
                  <Loader2 className="h-5 w-5 animate-spin text-primary-500 flex-shrink-0 mt-1" />
                ) : selectedSite === site.site_url ? (
                  <Check className="h-5 w-5 text-primary-500 flex-shrink-0 mt-1" />
                ) : null}
              </div>
            </button>
          ))}
        </div>
      )}

      {!isLoading && sites.length > 0 && (
        <div className="mt-6 p-4 bg-surface-secondary rounded-xl">
          <p className="text-xs text-text-secondary">
            <strong className="text-text-primary">Note:</strong> You can change the selected
            site anytime from the analytics settings. Make sure you have the necessary
            permissions to access data for the selected property.
          </p>
        </div>
      )}
    </div>
  );

  if (showAsModal) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
          <Card>
            <CardContent className="p-6">{content}</CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return <Card><CardContent className="p-6">{content}</CardContent></Card>;
}
