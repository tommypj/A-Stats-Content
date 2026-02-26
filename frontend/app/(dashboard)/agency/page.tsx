"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Building2,
  Users,
  Globe,
  FileText,
  Plus,
  ExternalLink,
  Shield,
  Trash2,
  Mail,
  Check,
} from "lucide-react";
import { toast } from "sonner";
import { api, parseApiError, AgencyProfile, ClientWorkspace, Project } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const ALLOWED_FEATURE_OPTIONS = [
  { key: "analytics", label: "Analytics" },
  { key: "content", label: "Content" },
  { key: "social", label: "Social" },
];

const INPUT_CLASS =
  "w-full text-sm border border-surface-tertiary rounded-lg px-3 py-2 bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500";

function PortalStatusBadge({ enabled }: { enabled: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
        enabled
          ? "bg-green-100 text-green-700"
          : "bg-surface-tertiary text-text-muted"
      }`}
    >
      {enabled ? (
        <>
          <Check className="h-3 w-3" />
          Portal Active
        </>
      ) : (
        "Portal Off"
      )}
    </span>
  );
}

export default function AgencyPage() {
  const [profile, setProfile] = useState<AgencyProfile | null>(null);
  const [clients, setClients] = useState<ClientWorkspace[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isAddingClient, setIsAddingClient] = useState(false);
  const [deletingClientId, setDeletingClientId] = useState<string | null>(null);
  const [togglingPortalId, setTogglingPortalId] = useState<string | null>(null);

  const [showSetup, setShowSetup] = useState(false);
  const [showAddClient, setShowAddClient] = useState(false);

  const [setupForm, setSetupForm] = useState({
    agency_name: "",
    contact_email: "",
    logo_url: "",
    brand_color_primary: "#6366f1",
    brand_color_secondary: "#8b5cf6",
    brand_color_accent: "#ec4899",
  });

  const [clientForm, setClientForm] = useState({
    project_id: "",
    client_name: "",
    client_email: "",
    allowed_features: {
      analytics: true,
      content: true,
      social: false,
    },
  });

  const loadProfile = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await api.agency.getProfile();
      setProfile(data);
      setShowSetup(false);
      // Load clients alongside profile
      const clientData = await api.agency.clients();
      setClients(clientData.items);
    } catch (err: unknown) {
      const apiErr = err as { response?: { status?: number } };
      if (apiErr?.response?.status === 404) {
        setShowSetup(true);
      } else {
        toast.error(parseApiError(err).message);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  // Load user projects for Add Client form
  useEffect(() => {
    api.projects.list().then(setProjects).catch(() => {});
  }, []);

  const handleCreateProfile = async () => {
    if (!setupForm.agency_name.trim()) {
      toast.error("Agency name is required");
      return;
    }
    try {
      setIsCreating(true);
      const brand_colors: Record<string, string> = {
        primary: setupForm.brand_color_primary,
        secondary: setupForm.brand_color_secondary,
        accent: setupForm.brand_color_accent,
      };
      const created = await api.agency.createProfile({
        agency_name: setupForm.agency_name.trim(),
        contact_email: setupForm.contact_email.trim() || undefined,
        logo_url: setupForm.logo_url.trim() || undefined,
        brand_colors,
      });
      setProfile(created);
      setClients([]);
      setShowSetup(false);
      toast.success("Agency profile created");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsCreating(false);
    }
  };

  const handleAddClient = async () => {
    if (!clientForm.project_id) {
      toast.error("Please select a project");
      return;
    }
    if (!clientForm.client_name.trim()) {
      toast.error("Client name is required");
      return;
    }
    try {
      setIsAddingClient(true);
      const created = await api.agency.createClient({
        project_id: clientForm.project_id,
        client_name: clientForm.client_name.trim(),
        client_email: clientForm.client_email.trim() || undefined,
        allowed_features: clientForm.allowed_features,
      });
      setClients((prev) => [...prev, created]);
      setShowAddClient(false);
      setClientForm({
        project_id: "",
        client_name: "",
        client_email: "",
        allowed_features: { analytics: true, content: true, social: false },
      });
      toast.success("Client workspace created");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsAddingClient(false);
    }
  };

  const handleDeleteClient = async (id: string) => {
    try {
      setDeletingClientId(id);
      await api.agency.deleteClient(id);
      setClients((prev) => prev.filter((c) => c.id !== id));
      toast.success("Client workspace removed");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setDeletingClientId(null);
    }
  };

  const handleTogglePortal = async (client: ClientWorkspace) => {
    try {
      setTogglingPortalId(client.id);
      const updated = client.is_portal_enabled
        ? await api.agency.disablePortal(client.id)
        : await api.agency.enablePortal(client.id);
      setClients((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      toast.success(
        updated.is_portal_enabled ? "Portal enabled" : "Portal disabled"
      );
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setTogglingPortalId(null);
    }
  };

  // --- Loading skeleton ---
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-10 w-64 bg-surface-tertiary animate-pulse rounded-2xl" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-28 bg-surface-tertiary animate-pulse rounded-2xl" />
          ))}
        </div>
        <div className="h-64 bg-surface-tertiary animate-pulse rounded-2xl" />
      </div>
    );
  }

  // --- Setup state ---
  if (showSetup) {
    return (
      <div className="max-w-lg mx-auto space-y-6 py-12">
        <div className="text-center">
          <div className="inline-flex items-center justify-center h-16 w-16 rounded-2xl bg-primary-50 mb-4">
            <Building2 className="h-8 w-8 text-primary-500" />
          </div>
          <h1 className="text-2xl font-bold text-text-primary">Set Up Your Agency</h1>
          <p className="text-text-secondary mt-2 text-sm">
            Create your white-label agency profile to manage client workspaces and branded reports.
          </p>
        </div>

        <Card>
          <CardContent className="p-6 space-y-4">
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">
                Agency Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={setupForm.agency_name}
                onChange={(e) =>
                  setSetupForm((p) => ({ ...p, agency_name: e.target.value }))
                }
                placeholder="Acme Digital Agency"
                className={INPUT_CLASS}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">
                Contact Email
              </label>
              <input
                type="email"
                value={setupForm.contact_email}
                onChange={(e) =>
                  setSetupForm((p) => ({ ...p, contact_email: e.target.value }))
                }
                placeholder="hello@acmeagency.com"
                className={INPUT_CLASS}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">
                Logo URL
              </label>
              <input
                type="url"
                value={setupForm.logo_url}
                onChange={(e) =>
                  setSetupForm((p) => ({ ...p, logo_url: e.target.value }))
                }
                placeholder="https://acmeagency.com/logo.png"
                className={INPUT_CLASS}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">
                Brand Colors
              </label>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { key: "brand_color_primary", label: "Primary" },
                  { key: "brand_color_secondary", label: "Secondary" },
                  { key: "brand_color_accent", label: "Accent" },
                ].map(({ key, label }) => (
                  <div key={key}>
                    <p className="text-xs text-text-muted mb-1">{label}</p>
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={setupForm[key as keyof typeof setupForm]}
                        onChange={(e) =>
                          setSetupForm((p) => ({ ...p, [key]: e.target.value }))
                        }
                        className="h-9 w-9 rounded-lg border border-surface-tertiary cursor-pointer p-0.5 bg-surface"
                      />
                      <input
                        type="text"
                        value={setupForm[key as keyof typeof setupForm]}
                        onChange={(e) =>
                          setSetupForm((p) => ({ ...p, [key]: e.target.value }))
                        }
                        className="flex-1 text-xs border border-surface-tertiary rounded-lg px-2 py-1.5 bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
                        maxLength={9}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <Button
              onClick={handleCreateProfile}
              variant="primary"
              className="w-full"
              disabled={isCreating || !setupForm.agency_name.trim()}
            >
              {isCreating ? "Creating..." : "Create Agency Profile"}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // --- Dashboard state ---
  const activePortals = clients.filter((c) => c.is_portal_enabled).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Agency Dashboard</h1>
          <p className="text-text-secondary mt-1 text-sm">
            Manage client workspaces, portals, and branded reports
          </p>
        </div>
        <Button
          onClick={() => setShowAddClient(true)}
          variant="primary"
          size="sm"
        >
          <Plus className="h-4 w-4 mr-1.5" />
          Add Client
        </Button>
      </div>

      {/* Agency Info Card */}
      <Card>
        <CardContent className="p-5">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            {profile?.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={profile.logo_url}
                alt="Agency logo"
                className="h-14 w-14 rounded-xl object-cover border border-surface-tertiary"
              />
            ) : (
              <div className="h-14 w-14 rounded-xl bg-primary-50 flex items-center justify-center flex-shrink-0">
                <Building2 className="h-7 w-7 text-primary-500" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-bold text-text-primary truncate">
                {profile?.agency_name}
              </h2>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1">
                {profile?.contact_email && (
                  <span className="flex items-center gap-1 text-xs text-text-secondary">
                    <Mail className="h-3.5 w-3.5" />
                    {profile.contact_email}
                  </span>
                )}
                {profile?.custom_domain && (
                  <span className="flex items-center gap-1 text-xs text-text-secondary">
                    <Globe className="h-3.5 w-3.5" />
                    {profile.custom_domain}
                  </span>
                )}
                <span className="flex items-center gap-1 text-xs text-text-secondary">
                  <Users className="h-3.5 w-3.5" />
                  {clients.length} / {profile?.max_clients ?? "—"} clients
                </span>
              </div>
            </div>
            {/* Brand color swatches */}
            {profile?.brand_colors && (
              <div className="flex items-center gap-1.5 flex-shrink-0">
                {Object.entries(profile.brand_colors).map(([name, color]) => (
                  <div
                    key={name}
                    title={`${name}: ${color}`}
                    className="h-5 w-5 rounded-full border border-surface-tertiary"
                    style={{ backgroundColor: color }}
                  />
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-text-secondary">Total Clients</p>
              <div className="h-9 w-9 rounded-xl bg-blue-50 flex items-center justify-center">
                <Users className="h-5 w-5 text-blue-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-text-primary">{clients.length}</p>
            <p className="text-xs text-text-muted mt-1">
              of {profile?.max_clients ?? "—"} max
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-text-secondary">Active Portals</p>
              <div className="h-9 w-9 rounded-xl bg-green-50 flex items-center justify-center">
                <Globe className="h-5 w-5 text-green-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-text-primary">{activePortals}</p>
            <p className="text-xs text-text-muted mt-1">client portals live</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-text-secondary">Reports Generated</p>
              <div className="h-9 w-9 rounded-xl bg-purple-50 flex items-center justify-center">
                <FileText className="h-5 w-5 text-purple-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-text-primary">—</p>
            <p className="text-xs text-text-muted mt-1">all time</p>
          </CardContent>
        </Card>
      </div>

      {/* Add Client Modal */}
      {showAddClient && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <Card className="w-full max-w-md shadow-2xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5 text-primary-500" />
                Add Client Workspace
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Project selector */}
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Project <span className="text-red-500">*</span>
                </label>
                <select
                  value={clientForm.project_id}
                  onChange={(e) =>
                    setClientForm((p) => ({ ...p, project_id: e.target.value }))
                  }
                  className={INPUT_CLASS}
                >
                  <option value="">Select a project...</option>
                  {projects.map((proj) => (
                    <option key={proj.id} value={proj.id}>
                      {proj.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Client Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={clientForm.client_name}
                  onChange={(e) =>
                    setClientForm((p) => ({ ...p, client_name: e.target.value }))
                  }
                  placeholder="Acme Corp"
                  className={INPUT_CLASS}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Client Email
                </label>
                <input
                  type="email"
                  value={clientForm.client_email}
                  onChange={(e) =>
                    setClientForm((p) => ({ ...p, client_email: e.target.value }))
                  }
                  placeholder="client@acme.com"
                  className={INPUT_CLASS}
                />
              </div>

              {/* Allowed features */}
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-2">
                  Allowed Features
                </label>
                <div className="space-y-2">
                  {ALLOWED_FEATURE_OPTIONS.map(({ key, label }) => (
                    <label
                      key={key}
                      className="flex items-center gap-2 cursor-pointer group"
                    >
                      <input
                        type="checkbox"
                        checked={
                          clientForm.allowed_features[
                            key as keyof typeof clientForm.allowed_features
                          ]
                        }
                        onChange={(e) =>
                          setClientForm((p) => ({
                            ...p,
                            allowed_features: {
                              ...p.allowed_features,
                              [key]: e.target.checked,
                            },
                          }))
                        }
                        className="h-4 w-4 rounded border-surface-tertiary text-primary-500 focus:ring-primary-500"
                      />
                      <span className="text-sm text-text-primary group-hover:text-primary-500 transition-colors">
                        {label}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex gap-2 pt-1">
                <Button
                  onClick={handleAddClient}
                  variant="primary"
                  size="sm"
                  disabled={
                    isAddingClient ||
                    !clientForm.project_id ||
                    !clientForm.client_name.trim()
                  }
                >
                  {isAddingClient ? "Adding..." : "Add Client"}
                </Button>
                <Button
                  onClick={() => {
                    setShowAddClient(false);
                    setClientForm({
                      project_id: "",
                      client_name: "",
                      client_email: "",
                      allowed_features: {
                        analytics: true,
                        content: true,
                        social: false,
                      },
                    });
                  }}
                  variant="ghost"
                  size="sm"
                >
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Client Workspace List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5 text-primary-500" />
              Client Workspaces
            </CardTitle>
            <Button
              onClick={() => setShowAddClient(true)}
              variant="outline"
              size="sm"
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Client
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {clients.length === 0 ? (
            <div className="text-center py-12">
              <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-surface-tertiary mb-4">
                <Users className="h-7 w-7 text-text-muted" />
              </div>
              <p className="text-sm font-medium text-text-secondary">No clients yet</p>
              <p className="text-xs text-text-muted mt-1 mb-4">
                Add your first client workspace to get started
              </p>
              <Button
                onClick={() => setShowAddClient(true)}
                variant="primary"
                size="sm"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add First Client
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {clients.map((client) => (
                <div
                  key={client.id}
                  className="p-4 rounded-xl border border-surface-tertiary hover:border-primary-500/30 hover:bg-surface-secondary transition-all group"
                >
                  {/* Client card header */}
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="h-9 w-9 rounded-lg bg-primary-50 flex items-center justify-center flex-shrink-0">
                        <Shield className="h-4 w-4 text-primary-500" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-text-primary truncate">
                          {client.client_name}
                        </p>
                        {client.client_email && (
                          <p className="text-xs text-text-muted truncate">
                            {client.client_email}
                          </p>
                        )}
                      </div>
                    </div>
                    <PortalStatusBadge enabled={client.is_portal_enabled} />
                  </div>

                  {/* Allowed features */}
                  {client.allowed_features && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {Object.entries(client.allowed_features)
                        .filter(([, enabled]) => enabled)
                        .map(([feature]) => (
                          <span
                            key={feature}
                            className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-surface-tertiary text-text-secondary capitalize"
                          >
                            {feature}
                          </span>
                        ))}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center gap-1.5 pt-2 border-t border-surface-tertiary">
                    <Link href={`/agency/clients/${client.id}`} className="flex-1">
                      <Button variant="secondary" size="sm" className="w-full">
                        <ExternalLink className="h-3.5 w-3.5 mr-1" />
                        View
                      </Button>
                    </Link>
                    <Button
                      onClick={() => handleTogglePortal(client)}
                      variant="outline"
                      size="sm"
                      disabled={togglingPortalId === client.id}
                      title={client.is_portal_enabled ? "Disable portal" : "Enable portal"}
                    >
                      <Globe className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      onClick={() => handleDeleteClient(client.id)}
                      variant="ghost"
                      size="sm"
                      disabled={deletingClientId === client.id}
                      title="Remove client"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-red-500" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
