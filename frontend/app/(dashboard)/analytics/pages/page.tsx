"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Search,
  Download,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";

import {
  api,
  parseApiError,
  PagePerformance,
  PagePerformanceListResponse,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GscConnectBanner } from "@/components/analytics/gsc-connect-banner";
import { cn } from "@/lib/utils";

type SortField = "page_url" | "clicks" | "impressions" | "ctr" | "position";
type SortOrder = "asc" | "desc";

export default function PagesPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [pages, setPages] = useState<PagePerformance[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>("clicks");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  useEffect(() => {
    checkStatus();
  }, []);

  useEffect(() => {
    if (isConnected) {
      loadPages();
    }
  }, [isConnected, currentPage]);

  async function checkStatus() {
    try {
      setIsLoading(true);
      const status = await api.analytics.status();
      setIsConnected(status.connected);
    } catch (error) {
      toast.error("Failed to check analytics status");
    } finally {
      setIsLoading(false);
    }
  }

  async function loadPages() {
    try {
      setIsLoading(true);
      const response: PagePerformanceListResponse = await api.analytics.pages({
        page: currentPage,
        page_size: pageSize,
      });
      setPages(response.items);
      setTotalPages(response.pages);
      setTotal(response.total);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to load pages");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleConnect() {
    try {
      setIsConnecting(true);
      const response = await api.analytics.getAuthUrl();
      window.location.href = response.auth_url;
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to initiate Google connection");
      setIsConnecting(false);
    }
  }

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  }

  function getSortedAndFilteredPages() {
    let filtered = pages;

    if (searchQuery) {
      filtered = pages.filter((p) =>
        p.page_url.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    const sorted = [...filtered].sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];

      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortOrder === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      return sortOrder === "asc"
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number);
    });

    return sorted;
  }

  function exportToCSV() {
    try {
      const data = getSortedAndFilteredPages();
      const headers = ["Page URL", "Clicks", "Impressions", "CTR", "Position"];
      const rows = data.map((p) => [
        p.page_url,
        p.clicks,
        p.impressions,
        (p.ctr * 100).toFixed(2) + "%",
        p.position.toFixed(1),
      ]);

      const csvContent = [
        headers.join(","),
        ...rows.map((row) => row.map((cell) => `"${cell}"`).join(",")),
      ].join("\n");

      const blob = new Blob([csvContent], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pages-${new Date().toISOString().split("T")[0]}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Export failed");
    }
  }

  function truncateUrl(url: string, maxLength: number = 60) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength - 3) + "...";
  }

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("en-US").format(Math.round(num));
  };

  if (isLoading && !isConnected) {
    return (
      <div className="space-y-6">
        <div className="h-32 bg-surface-tertiary animate-pulse rounded-2xl" />
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="space-y-6">
        <div>
          <Link
            href="/analytics"
            className="text-sm text-primary-600 hover:text-primary-700 mb-4 inline-block"
          >
            ← Back to Analytics
          </Link>
          <h1 className="font-display text-3xl font-bold text-text-primary">
            Page Performance
          </h1>
          <p className="mt-2 text-text-secondary">
            Connect Google Search Console to view page performance
          </p>
        </div>
        <GscConnectBanner onConnect={handleConnect} isLoading={isConnecting} />
      </div>
    );
  }

  const displayedPages = getSortedAndFilteredPages();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/analytics"
          className="text-sm text-primary-600 hover:text-primary-700 mb-4 inline-block"
        >
          ← Back to Analytics
        </Link>
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-text-primary">
              Page Performance
            </h1>
            <p className="mt-2 text-text-secondary">
              {total} pages tracked
            </p>
          </div>
          <Button
            variant="outline"
            onClick={exportToCSV}
            leftIcon={<Download className="h-4 w-4" />}
          >
            Export CSV
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
            <input
              type="text"
              placeholder="Search page URLs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-surface-tertiary rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </CardContent>
      </Card>

      {/* Pages Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-surface-tertiary">
                <tr>
                  <th className="text-left p-4 text-sm font-semibold text-text-primary">
                    <button
                      onClick={() => handleSort("page_url")}
                      className="flex items-center gap-2 hover:text-primary-600"
                    >
                      Page URL
                      {sortField === "page_url" ? (
                        sortOrder === "asc" ? (
                          <ArrowUp className="h-4 w-4" />
                        ) : (
                          <ArrowDown className="h-4 w-4" />
                        )
                      ) : (
                        <ArrowUpDown className="h-4 w-4 opacity-30" />
                      )}
                    </button>
                  </th>
                  <th className="text-right p-4 text-sm font-semibold text-text-primary">
                    <button
                      onClick={() => handleSort("clicks")}
                      className="flex items-center gap-2 hover:text-primary-600 ml-auto"
                    >
                      Clicks
                      {sortField === "clicks" ? (
                        sortOrder === "asc" ? (
                          <ArrowUp className="h-4 w-4" />
                        ) : (
                          <ArrowDown className="h-4 w-4" />
                        )
                      ) : (
                        <ArrowUpDown className="h-4 w-4 opacity-30" />
                      )}
                    </button>
                  </th>
                  <th className="text-right p-4 text-sm font-semibold text-text-primary">
                    <button
                      onClick={() => handleSort("impressions")}
                      className="flex items-center gap-2 hover:text-primary-600 ml-auto"
                    >
                      Impressions
                      {sortField === "impressions" ? (
                        sortOrder === "asc" ? (
                          <ArrowUp className="h-4 w-4" />
                        ) : (
                          <ArrowDown className="h-4 w-4" />
                        )
                      ) : (
                        <ArrowUpDown className="h-4 w-4 opacity-30" />
                      )}
                    </button>
                  </th>
                  <th className="text-right p-4 text-sm font-semibold text-text-primary">
                    <button
                      onClick={() => handleSort("ctr")}
                      className="flex items-center gap-2 hover:text-primary-600 ml-auto"
                    >
                      CTR
                      {sortField === "ctr" ? (
                        sortOrder === "asc" ? (
                          <ArrowUp className="h-4 w-4" />
                        ) : (
                          <ArrowDown className="h-4 w-4" />
                        )
                      ) : (
                        <ArrowUpDown className="h-4 w-4 opacity-30" />
                      )}
                    </button>
                  </th>
                  <th className="text-right p-4 text-sm font-semibold text-text-primary">
                    <button
                      onClick={() => handleSort("position")}
                      className="flex items-center gap-2 hover:text-primary-600 ml-auto"
                    >
                      Position
                      {sortField === "position" ? (
                        sortOrder === "asc" ? (
                          <ArrowUp className="h-4 w-4" />
                        ) : (
                          <ArrowDown className="h-4 w-4" />
                        )
                      ) : (
                        <ArrowUpDown className="h-4 w-4 opacity-30" />
                      )}
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  Array.from({ length: 10 }).map((_, i) => (
                    <tr key={i} className="border-b border-surface-tertiary">
                      <td className="p-4">
                        <div className="h-4 bg-surface-tertiary animate-pulse rounded w-96" />
                      </td>
                      <td className="p-4">
                        <div className="h-4 bg-surface-tertiary animate-pulse rounded w-16 ml-auto" />
                      </td>
                      <td className="p-4">
                        <div className="h-4 bg-surface-tertiary animate-pulse rounded w-16 ml-auto" />
                      </td>
                      <td className="p-4">
                        <div className="h-4 bg-surface-tertiary animate-pulse rounded w-16 ml-auto" />
                      </td>
                      <td className="p-4">
                        <div className="h-4 bg-surface-tertiary animate-pulse rounded w-16 ml-auto" />
                      </td>
                    </tr>
                  ))
                ) : displayedPages.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-text-muted">
                      {searchQuery ? "No pages found matching your search" : "No pages data available"}
                    </td>
                  </tr>
                ) : (
                  displayedPages.map((pageData) => (
                    <tr
                      key={pageData.page_url}
                      className="border-b border-surface-tertiary hover:bg-surface-secondary transition-colors"
                    >
                      <td className="p-4 text-sm text-text-primary font-medium max-w-2xl">
                        <div className="flex items-center gap-2">
                          <a
                            href={pageData.page_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-primary-600 transition-colors flex items-center gap-1 group"
                            title={pageData.page_url}
                          >
                            <span>{truncateUrl(pageData.page_url)}</span>
                            <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </a>
                        </div>
                      </td>
                      <td className="p-4 text-sm text-text-primary text-right">
                        {formatNumber(pageData.clicks)}
                      </td>
                      <td className="p-4 text-sm text-text-primary text-right">
                        {formatNumber(pageData.impressions)}
                      </td>
                      <td className="p-4 text-sm text-text-primary text-right">
                        {(pageData.ctr * 100).toFixed(2)}%
                      </td>
                      <td className="p-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <span className="text-sm text-text-primary">
                            {pageData.position.toFixed(1)}
                          </span>
                          {pageData.position_change !== undefined && pageData.position_change !== 0 && (
                            <span
                              className={cn(
                                "flex items-center gap-1 text-xs font-medium",
                                pageData.position_change < 0
                                  ? "text-green-600"
                                  : "text-red-600"
                              )}
                            >
                              {pageData.position_change < 0 ? (
                                <TrendingUp className="h-3 w-3" />
                              ) : (
                                <TrendingDown className="h-3 w-3" />
                              )}
                              {Math.abs(pageData.position_change).toFixed(1)}
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between p-4 border-t border-surface-tertiary">
              <div className="text-sm text-text-muted">
                Page {currentPage} of {totalPages}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  leftIcon={<ChevronLeft className="h-4 w-4" />}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  rightIcon={<ChevronRight className="h-4 w-4" />}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
