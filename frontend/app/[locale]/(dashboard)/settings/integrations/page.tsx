"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { CheckCircle, XCircle, Loader2, ExternalLink, AlertCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, parseApiError } from "@/lib/api";

interface Integration {
  id: string;
  name: string;
  description: string;
  icon: string;
  connected: boolean;
}

export default function IntegrationsSettingsPage() {
  const t = useTranslations("settings.integrations");

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

  const [integrations, setIntegrations] = useState<Integration[]>([
    {
      id: "gsc",
      name: "Google Search Console",
      description: t("gsc.description"),
      icon: "G",
      connected: false,
    },
  ]);

  useEffect(() => {
    checkWordPressStatus();
  }, []);

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
    } catch (error) {
      console.error("Failed to check WordPress status:", error);
    } finally {
      setLoadingStatus(false);
    }
  }

  async function handleWordPressConnect() {
    if (!wpFormData.site_url || !wpFormData.username || !wpFormData.app_password) {
      toast.error("Please fill in all fields");
      return;
    }
    if (!/^https?:\/\//i.test(wpFormData.site_url)) {
      toast.error("WordPress site URL must start with http:// or https://");
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
      // Test by attempting to fetch categories
      await api.wordpress.connect(wpFormData);
      toast.success("Connection test successful!");
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message || "Connection test failed");
    } finally {
      setWpTesting(false);
    }
  }

  const handleConnect = async (id: string) => {
    toast.info("Integration coming soon!");
  };

  const handleDisconnect = async (id: string) => {
    setIntegrations((prev) =>
      prev.map((i) => (i.id === id ? { ...i, connected: false } : i))
    );
    toast.success("Integration disconnected");
  };

  return (
    <div className="space-y-6">
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
            // Connected State
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-green-50 border border-green-200">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-green-900">Site URL</span>
                    {/^https?:\/\//i.test(wpSiteUrl) ? (
                      <a
                        href={wpSiteUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-green-700 hover:text-green-800 flex items-center gap-1"
                      >
                        {wpSiteUrl}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      <span className="text-sm text-green-700">{wpSiteUrl}</span>
                    )}
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
            // Not Connected State
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
                // Connection Form
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

                  {/* Help Text */}
                  <div className="p-4 rounded-xl bg-blue-50 border border-blue-200">
                    <div className="flex gap-3">
                      <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                      <div className="space-y-2 text-sm text-blue-900">
                        <p className="font-medium">How to get an Application Password:</p>
                        <ol className="list-decimal list-inside space-y-1 ml-2">
                          <li>Log in to your WordPress admin dashboard</li>
                          <li>Go to Users → Profile</li>
                          <li>Scroll down to "Application Passwords"</li>
                          <li>Enter a name (e.g., "A-Stats") and click "Add New Application Password"</li>
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

      {/* Other Integrations */}
      <div className="card">
        <div className="p-6 border-b border-surface-tertiary">
          <h2 className="font-display text-lg font-semibold text-text-primary">
            Other Integrations
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            Connect additional services to enhance your workflow
          </p>
        </div>

        <div className="p-6 space-y-4">
          {integrations.map((integration) => (
            <div
              key={integration.id}
              className="flex items-center justify-between p-4 rounded-xl border border-surface-tertiary"
            >
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-xl bg-surface-secondary flex items-center justify-center">
                  <span className="text-lg font-bold text-text-primary">
                    {integration.icon}
                  </span>
                </div>
                <div>
                  <p className="font-medium text-text-primary">
                    {integration.name}
                  </p>
                  <p className="text-sm text-text-secondary">
                    {integration.description}
                  </p>
                </div>
              </div>
              {integration.connected ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDisconnect(integration.id)}
                >
                  Disconnect
                </Button>
              ) : (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleConnect(integration.id)}
                >
                  Connect
                </Button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
