"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { clsx } from "clsx";
import { toast } from "sonner";
import {
  User,
  Lock,
  CreditCard,
  Plug,
  CheckCircle,
  XCircle,
  Loader2,
  ExternalLink,
  AlertCircle,
  RefreshCw,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, parseApiError } from "@/lib/api";

const TABS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "password", label: "Password", icon: Lock },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "integrations", label: "Integrations", icon: Plug },
] as const;

export default function IntegrationsSettingsPage() {
  const router = useRouter();

  const handleTabChange = (tabId: string) => {
    if (tabId === "integrations") return;
    if (tabId === "profile") {
      router.push("/settings#profile");
    } else {
      router.push(`/settings#${tabId}`);
    }
  };

  // WordPress connection state
  const [wpConnected, setWpConnected] = useState(false);
  const [wpSiteUrl, setWpSiteUrl] = useState("");
  const [wpUsername, setWpUsername] = useState("");
  const [wpSiteName, setWpSiteName] = useState("");
  const [loadingStatus, setLoadingStatus] = useState(true);

  // WordPress form state
  const [showWpForm, setShowWpForm] = useState(false);
  const [wpFormData, setWpFormData] = useState({
    site_url: "",
    username: "",
    app_password: "",
  });
  const [wpConnecting, setWpConnecting] = useState(false);
  const [wpDisconnecting, setWpDisconnecting] = useState(false);
  const [wpTesting, setWpTesting] = useState(false);

  // GSC connection state
  const [gscConnected, setGscConnected] = useState(false);
  const [gscSiteUrl, setGscSiteUrl] = useState<string | undefined>(undefined);
  const [gscLastSync, setGscLastSync] = useState<string | undefined>(undefined);
  const [gscLoadingStatus, setGscLoadingStatus] = useState(true);
  const [gscConnecting, setGscConnecting] = useState(false);
  const [gscDisconnecting, setGscDisconnecting] = useState(false);
  const [gscSyncing, setGscSyncing] = useState(false);

  // GSC site selection state
  const [gscAvailableSites, setGscAvailableSites] = useState<
    { site_url: string; permission_level: string }[]
  >([]);
  const [gscLoadingSites, setGscLoadingSites] = useState(false);
  const [gscSelectedSite, setGscSelectedSite] = useState("");
  const [gscSelectingSite, setGscSelectingSite] = useState(false);

  useEffect(() => {
    checkWordPressStatus();
    checkGscStatus();
  }, []);

  // Re-check GSC status when the window regains focus (user returns from OAuth flow)
  useEffect(() => {
    function handleFocus() {
      if (!gscConnected) {
        checkGscStatus();
      }
    }
    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, [gscConnected]);

  async function checkWordPressStatus() {
    try {
      setLoadingStatus(true);
      const status = await api.wordpress.status();
      setWpConnected(status.is_connected);
      if (status.is_connected) {
        setWpSiteUrl(status.site_url || "");
        setWpUsername(status.username || "");
        setWpSiteName(status.site_name || "");
      }
    } catch {
      // WordPress status check is non-critical
    } finally {
      setLoadingStatus(false);
    }
  }

  const checkGscStatus = useCallback(async () => {
    try {
      setGscLoadingStatus(true);
      const status = await api.analytics.status();
      setGscConnected(status.connected);
      setGscSiteUrl(status.site_url);
      setGscLastSync(status.last_sync);

      // If connected but no site selected, fetch available sites
      if (status.connected && !status.site_url) {
        fetchGscSites();
      }
    } catch {
      // GSC status check is non-critical
    } finally {
      setGscLoadingStatus(false);
    }
  }, []);

  async function fetchGscSites() {
    try {
      setGscLoadingSites(true);
      const response = await api.analytics.sites();
      setGscAvailableSites(response.sites);
      if (response.sites.length > 0) {
        setGscSelectedSite(response.sites[0].site_url);
      }
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setGscLoadingSites(false);
    }
  }

  async function handleGscConnect() {
    setGscConnecting(true);
    try {
      const { auth_url } = await api.analytics.getAuthUrl();
      window.open(auth_url, "_blank", "noopener");
      toast.info("Complete the Google sign-in in the new tab, then return here.");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setGscConnecting(false);
    }
  }

  async function handleGscSelectSite() {
    if (!gscSelectedSite) {
      toast.error("Please select a site");
      return;
    }
    setGscSelectingSite(true);
    try {
      const updated = await api.analytics.selectSite(gscSelectedSite);
      setGscSiteUrl(updated.site_url);
      setGscAvailableSites([]);
      toast.success("Site selected successfully");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setGscSelectingSite(false);
    }
  }

  async function handleGscSync() {
    setGscSyncing(true);
    try {
      const result = await api.analytics.sync();
      toast.success(result.message || "Sync started successfully");
      // Refresh status to get updated last_sync time
      await checkGscStatus();
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setGscSyncing(false);
    }
  }

  async function handleGscDisconnect() {
    setGscDisconnecting(true);
    try {
      await api.analytics.disconnect();
      setGscConnected(false);
      setGscSiteUrl(undefined);
      setGscLastSync(undefined);
      setGscAvailableSites([]);
      setGscSelectedSite("");
      toast.success("Disconnected from Google Search Console");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setGscDisconnecting(false);
    }
  }

  async function handleWordPressConnect() {
    if (!wpFormData.site_url || !wpFormData.username || !wpFormData.app_password) {
      toast.error("Please fill in all fields");
      return;
    }

    setWpConnecting(true);
    try {
      const result = await api.wordpress.connect(wpFormData);
      setWpConnected(true);
      setWpSiteUrl(result.site_url);
      setWpUsername(result.username);
      setWpSiteName(result.site_name || "");
      setShowWpForm(false);
      setWpFormData({ site_url: "", username: "", app_password: "" });
      toast.success("Successfully connected to WordPress!");
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to connect to WordPress");
    } finally {
      setWpConnecting(false);
    }
  }

  async function handleWordPressDisconnect() {
    setWpDisconnecting(true);
    try {
      await api.wordpress.disconnect();
      setWpConnected(false);
      setWpSiteUrl("");
      setWpUsername("");
      setWpSiteName("");
      toast.success("Disconnected from WordPress");
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Failed to disconnect from WordPress");
    } finally {
      setWpDisconnecting(false);
    }
  }

  async function handleTestConnection() {
    if (!wpFormData.site_url || !wpFormData.username || !wpFormData.app_password) {
      toast.error("Please fill in all fields");
      return;
    }

    setWpTesting(true);
    try {
      await api.wordpress.connect(wpFormData);
      toast.success("Connection test successful!");
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Connection test failed");
    } finally {
      setWpTesting(false);
    }
  }

  return (
    <div className="space-y-6 max-w-3xl animate-in">
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Settings</h1>
        <p className="mt-1 text-text-secondary">Manage your account settings and preferences.</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 p-1 bg-surface-secondary rounded-xl">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
              tab.id === "integrations"
                ? "bg-surface text-text-primary shadow-sm"
                : "text-text-secondary hover:text-text-primary"
            )}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* WordPress Integration Card */}
      <div className="card">
        <div className="p-6 border-b border-surface-tertiary">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
                <span className="text-xl font-bold text-white">W</span>
              </div>
              <div>
                <h3 className="font-display text-lg font-semibold text-text-primary">
                  WordPress
                </h3>
                <p className="text-sm text-text-secondary mt-0.5">
                  Publish articles directly to your WordPress site
                </p>
              </div>
            </div>
            {loadingStatus ? (
              <Loader2 className="h-5 w-5 animate-spin text-text-muted" />
            ) : wpConnected ? (
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="h-5 w-5" />
                <span className="text-sm font-medium">Connected</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-text-muted">
                <XCircle className="h-5 w-5" />
                <span className="text-sm font-medium">Not Connected</span>
              </div>
            )}
          </div>
        </div>

        <div className="p-6">
          {wpConnected ? (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-green-50 border border-green-200">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-green-900">Site URL</span>
                    <a
                      href={wpSiteUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-green-700 hover:text-green-800 flex items-center gap-1"
                    >
                      {wpSiteUrl}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                  {wpSiteName && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-green-900">Site Name</span>
                      <span className="text-sm text-green-700">{wpSiteName}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-green-900">Username</span>
                    <span className="text-sm text-green-700">{wpUsername}</span>
                  </div>
                </div>
              </div>

              <Button
                variant="outline"
                onClick={handleWordPressDisconnect}
                isLoading={wpDisconnecting}
                className="w-full sm:w-auto"
              >
                Disconnect WordPress
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {!showWpForm ? (
                <div className="text-center py-8">
                  <p className="text-text-secondary mb-4">
                    Connect your WordPress site to publish articles directly
                  </p>
                  <Button onClick={() => setShowWpForm(true)}>
                    Connect WordPress
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  <Input
                    label="WordPress Site URL"
                    type="url"
                    placeholder="https://yoursite.com"
                    value={wpFormData.site_url}
                    onChange={(e) =>
                      setWpFormData({ ...wpFormData, site_url: e.target.value })
                    }
                    helperText="Enter your WordPress site URL (e.g., https://example.com)"
                  />

                  <Input
                    label="Username"
                    type="text"
                    placeholder="admin"
                    value={wpFormData.username}
                    onChange={(e) =>
                      setWpFormData({ ...wpFormData, username: e.target.value })
                    }
                    helperText="Your WordPress username"
                  />

                  <Input
                    label="Application Password"
                    type="password"
                    placeholder="xxxx xxxx xxxx xxxx xxxx xxxx"
                    value={wpFormData.app_password}
                    onChange={(e) =>
                      setWpFormData({ ...wpFormData, app_password: e.target.value })
                    }
                    helperText="Generate an application password in WordPress"
                  />

                  <div className="p-4 rounded-xl bg-blue-50 border border-blue-200">
                    <div className="flex gap-3">
                      <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                      <div className="space-y-2 text-sm text-blue-900">
                        <p className="font-medium">How to get an Application Password:</p>
                        <ol className="list-decimal list-inside space-y-1 ml-2">
                          <li>Log in to your WordPress admin dashboard</li>
                          <li>Go to Users &rarr; Profile</li>
                          <li>Scroll down to &ldquo;Application Passwords&rdquo;</li>
                          <li>Enter a name (e.g., &ldquo;A-Stats&rdquo;) and click &ldquo;Add New Application Password&rdquo;</li>
                          <li>Copy the generated password and paste it above</li>
                        </ol>
                        <p className="text-xs mt-2 text-blue-700">
                          Note: Application Passwords require WordPress 5.6+ and HTTPS
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <Button
                      variant="outline"
                      onClick={() => setShowWpForm(false)}
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={handleTestConnection}
                      isLoading={wpTesting}
                      className="flex-1"
                    >
                      Test Connection
                    </Button>
                    <Button
                      onClick={handleWordPressConnect}
                      isLoading={wpConnecting}
                      className="flex-1"
                    >
                      Connect
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Google Search Console Integration Card */}
      <div className="card">
        <div className="p-6 border-b border-surface-tertiary">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-green-500 to-blue-500 flex items-center justify-center">
                <span className="text-xl font-bold text-white">G</span>
              </div>
              <div>
                <h3 className="font-display text-lg font-semibold text-text-primary">
                  Google Search Console
                </h3>
                <p className="text-sm text-text-secondary mt-0.5">
                  Track keyword rankings and search performance data
                </p>
              </div>
            </div>
            {gscLoadingStatus ? (
              <Loader2 className="h-5 w-5 animate-spin text-text-muted" />
            ) : gscConnected ? (
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="h-5 w-5" />
                <span className="text-sm font-medium">Connected</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-text-muted">
                <XCircle className="h-5 w-5" />
                <span className="text-sm font-medium">Not Connected</span>
              </div>
            )}
          </div>
        </div>

        <div className="p-6">
          {gscLoadingStatus ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
            </div>
          ) : gscConnected ? (
            <div className="space-y-4">
              {gscSiteUrl ? (
                /* Connected with site selected */
                <div className="p-4 rounded-xl bg-green-50 border border-green-200">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-green-900">Connected Site</span>
                      <a
                        href={`https://search.google.com/search-console?resource_id=${encodeURIComponent(gscSiteUrl)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-green-700 hover:text-green-800 flex items-center gap-1"
                      >
                        {gscSiteUrl}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                    {gscLastSync && (
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-green-900">Last Sync</span>
                        <span className="text-sm text-green-700">
                          {new Date(gscLastSync).toLocaleString()}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                /* Connected but no site selected yet */
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-blue-50 border border-blue-200">
                    <div className="flex gap-3">
                      <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-blue-900">
                        Google Search Console is connected. Select a verified site to start tracking.
                      </p>
                    </div>
                  </div>

                  {gscLoadingSites ? (
                    <div className="flex items-center gap-2 text-text-muted">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span className="text-sm">Loading verified sites...</span>
                    </div>
                  ) : gscAvailableSites.length > 0 ? (
                    <div className="space-y-3">
                      <label className="block text-sm font-medium text-text-primary">
                        Select a site to track
                      </label>
                      <select
                        value={gscSelectedSite}
                        onChange={(e) => setGscSelectedSite(e.target.value)}
                        className="w-full rounded-lg border border-surface-tertiary bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                      >
                        {gscAvailableSites.map((site) => (
                          <option key={site.site_url} value={site.site_url}>
                            {site.site_url} ({site.permission_level})
                          </option>
                        ))}
                      </select>
                      <Button
                        onClick={handleGscSelectSite}
                        isLoading={gscSelectingSite}
                        className="w-full sm:w-auto"
                      >
                        Confirm Site Selection
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <p className="text-sm text-text-secondary">
                        No verified sites found. Make sure you have at least one verified property in Google Search Console.
                      </p>
                      <Button
                        variant="outline"
                        onClick={fetchGscSites}
                        className="w-full sm:w-auto"
                      >
                        Refresh Sites
                      </Button>
                    </div>
                  )}
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                {gscSiteUrl && (
                  <Button
                    variant="secondary"
                    onClick={handleGscSync}
                    isLoading={gscSyncing}
                    className="flex items-center gap-2"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Sync Data
                  </Button>
                )}
                <Button
                  variant="outline"
                  onClick={handleGscDisconnect}
                  isLoading={gscDisconnecting}
                >
                  Disconnect GSC
                </Button>
              </div>
            </div>
          ) : (
            /* Not connected */
            <div className="text-center py-8">
              <p className="text-text-secondary mb-2">
                Connect your Google Search Console account to import keyword rankings and search performance data.
              </p>
              <p className="text-xs text-text-muted mb-6">
                You will be redirected to Google to authorize access. Return to this page once complete.
              </p>
              <Button
                onClick={handleGscConnect}
                isLoading={gscConnecting}
              >
                Connect Google Search Console
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
