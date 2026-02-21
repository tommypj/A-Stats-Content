"use client";

import { AlertCircle, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface GscConnectBannerProps {
  onConnect: () => void;
  isLoading?: boolean;
}

export function GscConnectBanner({ onConnect, isLoading = false }: GscConnectBannerProps) {
  return (
    <Card className="border-2 border-primary-200 bg-primary-50">
      <div className="p-6">
        <div className="flex items-start gap-4">
          <div className="h-12 w-12 rounded-xl bg-primary-500 flex items-center justify-center flex-shrink-0">
            <AlertCircle className="h-6 w-6 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="font-display text-lg font-semibold text-text-primary">
              Connect Google Search Console
            </h3>
            <p className="mt-1 text-sm text-text-secondary">
              Connect your Google Search Console account to start tracking your website's
              performance, keywords, and rankings.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Button onClick={onConnect} isLoading={isLoading}>
                <ExternalLink className="h-4 w-4 mr-2" />
                Connect Google Search Console
              </Button>
              <a
                href="https://search.google.com/search-console"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button variant="outline">
                  Learn More
                  <ExternalLink className="h-4 w-4 ml-2" />
                </Button>
              </a>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
