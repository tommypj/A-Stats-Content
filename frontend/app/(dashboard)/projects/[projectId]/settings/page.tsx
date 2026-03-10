"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  api,
  ProjectUpdateRequest,
  ProjectInvitationCreateRequest,
  ProjectRole,
  parseApiError,
} from "@/lib/api";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ProjectSettingsGeneral } from "@/components/project/project-settings-general";
import { ProjectMembersList } from "@/components/project/project-members-list";
import { ProjectInvitationsList } from "@/components/project/project-invitations-list";
import { InviteMemberForm } from "@/components/project/invite-member-form";
import { TransferOwnershipModal } from "@/components/project/transfer-ownership-modal";
import { DeleteProjectModal } from "@/components/project/delete-project-modal";
import {
  ArrowLeft,
  Settings,
  Users,
  Mail,
  AlertTriangle,
  Crown,
  LogOut,
  Plug,
  Globe,
  Search,
  CheckCircle,
  ExternalLink,
  Unplug,
  Loader2,
} from "lucide-react";
import { TierGate } from "@/components/ui/tier-gate";

type Tab = "general" | "members" | "invitations" | "integrations" | "danger";

const tabs = [
  { id: "general" as Tab, label: "General", icon: Settings },
  { id: "members" as Tab, label: "Members", icon: Users },
  { id: "invitations" as Tab, label: "Invitations", icon: Mail },
  { id: "integrations" as Tab, label: "Integrations", icon: Plug },
  { id: "danger" as Tab, label: "Danger Zone", icon: AlertTriangle },
];

export default function ProjectSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<Tab>("general");

  // Modal state
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ action: () => void; title: string; message: string; confirmLabel?: string; variant?: "danger" | "warning" | "default" } | null>(null);

  // WordPress form state (local only — not fetched data)
  const [showWpForm, setShowWpForm] = useState(false);
  const [wpFormSiteUrl, setWpFormSiteUrl] = useState("");
  const [wpFormUsername, setWpFormUsername] = useState("");
  const [wpFormAppPassword, setWpFormAppPassword] = useState("");
  const [wpError, setWpError] = useState("");

  // GSC local state
  const [gscError, setGscError] = useState("");

  // --- React Query: project data ---

  const projectQueryKey = ["projects", projectId];
  const membersQueryKey = ["projects", projectId, "members"];
  const invitationsQueryKey = ["projects", projectId, "invitations"];

  const { data: project, isLoading: projectLoading, error: projectError } = useQuery({
    queryKey: projectQueryKey,
    queryFn: () => api.projects.get(projectId),
    staleTime: 30_000,
  });

  const { data: members = [], isLoading: membersLoading } = useQuery({
    queryKey: membersQueryKey,
    queryFn: () => api.projects.members.list(projectId),
    staleTime: 30_000,
  });

  const { data: invitations = [], isLoading: invitationsLoading } = useQuery({
    queryKey: invitationsQueryKey,
    queryFn: () => api.projects.invitations.list(projectId),
    staleTime: 30_000,
  });

  const isLoading = projectLoading || membersLoading || invitationsLoading;
  const error = projectError ? parseApiError(projectError).message : "";

  // --- React Query: integrations (only when tab is active) ---

  const { data: wpStatus, isLoading: wpLoadingStatus } = useQuery({
    queryKey: ["wordpress", "status"],
    queryFn: async () => {
      try {
        return await api.wordpress.status();
      } catch {
        return { is_connected: false, site_url: "", username: "", site_name: "" };
      }
    },
    enabled: activeTab === "integrations",
    staleTime: 30_000,
  });

  const wpConnected = wpStatus?.is_connected ?? false;
  const wpSiteUrl = wpStatus?.site_url || "";
  const wpUsername = wpStatus?.username || "";
  const wpSiteName = wpStatus?.site_name || "";

  const { data: gscStatus, isLoading: gscLoadingStatus } = useQuery({
    queryKey: ["gsc", "status"],
    queryFn: async () => {
      try {
        return await api.analytics.status();
      } catch {
        return { connected: false, site_url: "", last_sync: "" };
      }
    },
    enabled: activeTab === "integrations",
    staleTime: 30_000,
    refetchOnWindowFocus: true,
  });

  const gscConnected = gscStatus?.connected ?? false;
  const gscSiteUrl = gscStatus?.site_url || "";
  const gscLastSync = gscStatus?.last_sync || "";

  // --- Mutations ---

  const invalidateProjectData = () => {
    queryClient.invalidateQueries({ queryKey: projectQueryKey });
    queryClient.invalidateQueries({ queryKey: membersQueryKey });
    queryClient.invalidateQueries({ queryKey: invitationsQueryKey });
  };

  const handleUpdateProject = async (data: ProjectUpdateRequest) => {
    try {
      const updated = await api.projects.update(projectId, data);
      queryClient.setQueryData(projectQueryKey, updated);
      toast.success("Project updated successfully!");
    } catch (err) {
      throw new Error(parseApiError(err).message);
    }
  };

  const handleUploadLogo = async (file: File) => {
    try {
      const updated = await api.projects.uploadLogo(projectId, file);
      queryClient.setQueryData(projectQueryKey, updated);
      toast.success("Logo uploaded successfully!");
    } catch (err) {
      throw new Error(parseApiError(err).message);
    }
  };

  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: ProjectRole }) =>
      api.projects.members.update(projectId, userId, { role }),
    onSuccess: () => {
      toast.success("Member role updated successfully!");
      invalidateProjectData();
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const handleUpdateRole = async (userId: string, role: ProjectRole) => {
    updateRoleMutation.mutate({ userId, role });
  };

  const removeMemberMutation = useMutation({
    mutationFn: ({ userId }: { userId: string; memberName: string }) =>
      api.projects.members.remove(projectId, userId),
    onSuccess: (_data, { memberName }) => {
      toast.success(`${memberName} has been removed from the project`);
      invalidateProjectData();
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const handleRemoveMember = async (userId: string, memberName: string) => {
    removeMemberMutation.mutate({ userId, memberName });
  };

  const inviteMemberMutation = useMutation({
    mutationFn: (data: ProjectInvitationCreateRequest) =>
      api.projects.invitations.create(projectId, data),
    onSuccess: (_data, variables) => {
      toast.success(`Invitation sent to ${variables.email}`);
      invalidateProjectData();
    },
    onError: (err) => {
      throw new Error(parseApiError(err).message);
    },
  });

  const handleInviteMember = async (data: ProjectInvitationCreateRequest) => {
    // The child component expects a thrown error for inline display
    await inviteMemberMutation.mutateAsync(data);
  };

  const revokeInvitationMutation = useMutation({
    mutationFn: (invitationId: string) =>
      api.projects.invitations.revoke(projectId, invitationId),
    onSuccess: () => {
      toast.success("Invitation revoked");
      invalidateProjectData();
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const handleRevokeInvitation = async (invitationId: string) => {
    revokeInvitationMutation.mutate(invitationId);
  };

  const resendInvitationMutation = useMutation({
    mutationFn: (invitationId: string) =>
      api.projects.invitations.resend(projectId, invitationId),
    onSuccess: () => {
      toast.success("Invitation resent");
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const handleResendInvitation = async (invitationId: string) => {
    resendInvitationMutation.mutate(invitationId);
  };

  const transferOwnershipMutation = useMutation({
    mutationFn: (newOwnerId: string) =>
      api.projects.transferOwnership(projectId, newOwnerId),
    onSuccess: () => {
      router.push("/projects");
      toast.success("Ownership transferred successfully. You are now an Admin.");
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const handleTransferOwnership = async (newOwnerId: string) => {
    transferOwnershipMutation.mutate(newOwnerId);
  };

  const deleteProjectMutation = useMutation({
    mutationFn: () => api.projects.delete(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      router.push("/projects");
      toast.success("Project deleted successfully");
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const handleDeleteProject = async () => {
    deleteProjectMutation.mutate();
  };

  const leaveProjectMutation = useMutation({
    mutationFn: () => api.projects.leave(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      router.push("/projects");
      toast.success("You have left the project");
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const handleLeaveProject = () => {
    setConfirmAction({
      action: () => {
        leaveProjectMutation.mutate();
      },
      title: "Leave Project",
      message: "Are you sure you want to leave this project? You will lose access immediately.",
      confirmLabel: "Leave Project",
      variant: "warning",
    });
  };

  // ---------------------------------------------------------------------------
  // Integrations mutations
  // ---------------------------------------------------------------------------

  const wpConnectMutation = useMutation({
    mutationFn: () =>
      api.wordpress.connect({
        site_url: wpFormSiteUrl,
        username: wpFormUsername,
        app_password: wpFormAppPassword,
      }),
    onSuccess: () => {
      setShowWpForm(false);
      setWpFormSiteUrl("");
      setWpFormUsername("");
      setWpFormAppPassword("");
      setWpError("");
      queryClient.invalidateQueries({ queryKey: ["wordpress", "status"] });
    },
    onError: (err) => {
      setWpError(parseApiError(err).message);
    },
  });

  const handleWpConnect = () => {
    setWpError("");
    if (!wpFormSiteUrl || !wpFormUsername || !wpFormAppPassword) {
      setWpError("All fields are required");
      return;
    }
    wpConnectMutation.mutate();
  };

  const wpDisconnectMutation = useMutation({
    mutationFn: () => api.wordpress.disconnect(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wordpress", "status"] });
    },
    onError: (err) => {
      setWpError(parseApiError(err).message);
    },
  });

  const handleWpDisconnect = () => {
    wpDisconnectMutation.mutate();
  };

  const gscConnectMutation = useMutation({
    mutationFn: () => api.analytics.getAuthUrl(),
    onSuccess: ({ auth_url }) => {
      window.open(auth_url, "_blank", "noopener,noreferrer");
    },
    onError: (err) => {
      setGscError(parseApiError(err).message);
    },
  });

  const handleGscConnect = () => {
    setGscError("");
    gscConnectMutation.mutate();
  };

  const gscDisconnectMutation = useMutation({
    mutationFn: () => api.analytics.disconnect(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gsc", "status"] });
    },
    onError: (err) => {
      setGscError(parseApiError(err).message);
    },
  });

  const handleGscDisconnect = () => {
    gscDisconnectMutation.mutate();
  };

  const wpConnecting = wpConnectMutation.isPending;
  const wpDisconnecting = wpDisconnectMutation.isPending;
  const gscConnecting = gscConnectMutation.isPending;
  const gscDisconnecting = gscDisconnectMutation.isPending;

  // ---------------------------------------------------------------------------

  const canManageSettings = project && (project.my_role === "owner" || project.my_role === "admin");
  const isOwner = project?.my_role === "owner";

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Card className="p-6">
          <Skeleton className="h-48" />
        </Card>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="space-y-6">
        <Link href="/projects">
          <Button variant="ghost" size="sm" leftIcon={<ArrowLeft className="h-4 w-4" />}>
            Back to Projects
          </Button>
        </Link>
        <Card className="p-6">
          <div className="text-center py-8">
            <p className="text-red-600 mb-4">{error || "Project not found"}</p>
            <Button onClick={() => invalidateProjectData()}>Retry</Button>
          </div>
        </Card>
      </div>
    );
  }

  if (!canManageSettings) {
    return (
      <div className="space-y-6">
        <Link href="/projects">
          <Button variant="ghost" size="sm" leftIcon={<ArrowLeft className="h-4 w-4" />}>
            Back to Projects
          </Button>
        </Link>
        <Card className="p-6">
          <div className="text-center py-8">
            <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
            <p className="text-text-primary font-semibold mb-2">Access Denied</p>
            <p className="text-text-muted">
              Only project owners and admins can access settings
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <TierGate minimum="starter" feature="Project Management">
    <div className="space-y-6">
      <ConfirmDialog
        isOpen={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={() => { confirmAction?.action(); setConfirmAction(null); }}
        title={confirmAction?.title ?? ""}
        message={confirmAction?.message ?? ""}
        variant={confirmAction?.variant ?? "default"}
        confirmLabel={confirmAction?.confirmLabel ?? "Confirm"}
      />

      {/* Header */}
      <div>
        <Link href="/projects">
          <Button variant="ghost" size="sm" leftIcon={<ArrowLeft className="h-4 w-4" />}>
            Back to Projects
          </Button>
        </Link>
        <div className="mt-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">{project.name} Settings</h1>
            <p className="text-text-secondary mt-1">Manage your project configuration</p>
          </div>
          <Badge className={`${project.my_role === "owner" ? "bg-yellow-100 text-yellow-800" : "bg-purple-100 text-purple-800"}`}>
            {project.my_role === "owner" && <Crown className="h-3 w-3 mr-1" />}
            {project.my_role.charAt(0).toUpperCase() + project.my_role.slice(1)}
          </Badge>
        </div>
      </div>

      {/* Tabs */}
      <Card className="p-2">
        <div className="flex items-center gap-1 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium text-sm transition-colors whitespace-nowrap ${
                  isActive
                    ? "bg-primary-50 text-primary-600"
                    : "text-text-secondary hover:text-text-primary hover:bg-surface-secondary"
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </Card>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === "general" && (
          <ProjectSettingsGeneral
            project={project}
            onUpdate={handleUpdateProject}
            onUploadLogo={handleUploadLogo}
          />
        )}

        {activeTab === "members" && (
          <ProjectMembersList
            members={members}
            myRole={project.my_role}
            onUpdateRole={handleUpdateRole}
            onRemove={handleRemoveMember}
          />
        )}

        {activeTab === "invitations" && (
          <div className="space-y-6">
            <InviteMemberForm onInvite={handleInviteMember} />
            <ProjectInvitationsList
              invitations={invitations}
              onRevoke={handleRevokeInvitation}
              onResend={handleResendInvitation}
            />
          </div>
        )}

        {activeTab === "integrations" && (
          <div className="space-y-6">
            {/* WordPress Integration */}
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <Globe className="h-5 w-5 text-primary-500" />
                <h2 className="text-lg font-display font-semibold text-text-primary">WordPress</h2>
              </div>

              {wpLoadingStatus ? (
                <div className="flex items-center gap-2 text-text-secondary">
                  <Loader2 className="h-4 w-4 animate-spin" /> Checking connection...
                </div>
              ) : wpConnected ? (
                <div className="space-y-4">
                  <div className="p-4 bg-green-50 border border-green-200 rounded-xl space-y-1">
                    <p className="flex items-center gap-2 text-sm font-medium text-green-800">
                      <CheckCircle className="h-4 w-4" /> Connected
                    </p>
                    {wpSiteName && (
                      <p className="text-sm text-green-700">Site: {wpSiteName}</p>
                    )}
                    <p className="text-sm text-green-700">URL: {wpSiteUrl}</p>
                    <p className="text-sm text-green-700">Username: {wpUsername}</p>
                  </div>
                  <Button
                    variant="outline"
                    onClick={handleWpDisconnect}
                    disabled={wpDisconnecting}
                    className="text-red-600 border-red-200 hover:bg-red-50"
                  >
                    {wpDisconnecting ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Unplug className="h-4 w-4 mr-2" />
                    )}
                    Disconnect
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  <p className="text-sm text-text-secondary">
                    Connect your WordPress site to publish articles directly from this project.
                  </p>

                  {!showWpForm ? (
                    <Button onClick={() => setShowWpForm(true)}>
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Connect WordPress
                    </Button>
                  ) : (
                    <div className="space-y-3 p-4 bg-surface-secondary rounded-xl">
                      <div>
                        <label htmlFor="site-url" className="block text-sm font-medium text-text-secondary mb-1">
                          Site URL
                        </label>
                        <Input
                          id="site-url"
                          value={wpFormSiteUrl}
                          onChange={(e) => setWpFormSiteUrl(e.target.value)}
                          placeholder="https://yoursite.com"
                        />
                      </div>
                      <div>
                        <label htmlFor="username" className="block text-sm font-medium text-text-secondary mb-1">
                          Username
                        </label>
                        <Input
                          id="username"
                          value={wpFormUsername}
                          onChange={(e) => setWpFormUsername(e.target.value)}
                          placeholder="WordPress username"
                        />
                      </div>
                      <div>
                        <label htmlFor="application-password" className="block text-sm font-medium text-text-secondary mb-1">
                          Application Password
                        </label>
                        <Input
                          id="application-password"
                          type="password"
                          value={wpFormAppPassword}
                          onChange={(e) => setWpFormAppPassword(e.target.value)}
                          placeholder="xxxx xxxx xxxx xxxx xxxx xxxx"
                        />
                        <p className="mt-1 text-xs text-text-muted">
                          Generate one in WordPress &rarr; Users &rarr; Profile &rarr; Application Passwords
                        </p>
                      </div>

                      {wpError && <p className="text-sm text-red-600">{wpError}</p>}

                      <div className="flex flex-wrap gap-2 pt-1">
                        <Button onClick={handleWpConnect} disabled={wpConnecting}>
                          {wpConnecting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                          Connect
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => {
                            setShowWpForm(false);
                            setWpError("");
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Card>

            {/* Google Search Console Integration */}
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <Search className="h-5 w-5 text-primary-500" />
                <h2 className="text-lg font-display font-semibold text-text-primary">
                  Google Search Console
                </h2>
              </div>

              {gscLoadingStatus ? (
                <div className="flex items-center gap-2 text-text-secondary">
                  <Loader2 className="h-4 w-4 animate-spin" /> Checking connection...
                </div>
              ) : gscConnected ? (
                <div className="space-y-4">
                  <div className="p-4 bg-green-50 border border-green-200 rounded-xl space-y-1">
                    <p className="flex items-center gap-2 text-sm font-medium text-green-800">
                      <CheckCircle className="h-4 w-4" /> Connected
                    </p>
                    {gscSiteUrl && (
                      <p className="text-sm text-green-700">Site: {gscSiteUrl}</p>
                    )}
                    {gscLastSync && (
                      <p className="text-sm text-green-700">
                        Last sync: {new Date(gscLastSync).toLocaleDateString("en-US")}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="outline"
                    onClick={handleGscDisconnect}
                    disabled={gscDisconnecting}
                    className="text-red-600 border-red-200 hover:bg-red-50"
                  >
                    {gscDisconnecting ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Unplug className="h-4 w-4 mr-2" />
                    )}
                    Disconnect
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  <p className="text-sm text-text-secondary">
                    Connect Google Search Console to track search performance and get keyword insights for this project.
                  </p>

                  {gscError && <p className="text-sm text-red-600">{gscError}</p>}

                  <Button onClick={handleGscConnect} disabled={gscConnecting}>
                    {gscConnecting ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <ExternalLink className="h-4 w-4 mr-2" />
                    )}
                    Connect Google Search Console
                  </Button>
                </div>
              )}
            </Card>
          </div>
        )}

        {activeTab === "danger" && (
          <div className="space-y-6">
            {/* Transfer Ownership */}
            {isOwner && (
              <Card className="p-6 border-yellow-200">
                <div className="flex items-start gap-4">
                  <Crown className="h-6 w-6 text-yellow-600 mt-1" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-text-primary mb-1">
                      Transfer Ownership
                    </h3>
                    <p className="text-sm text-text-secondary mb-4">
                      Transfer project ownership to another admin or member. You will become an Admin after transfer.
                    </p>
                    <Button variant="outline" onClick={() => setShowTransferModal(true)}>
                      Transfer Ownership
                    </Button>
                  </div>
                </div>
              </Card>
            )}

            {/* Leave Project */}
            {!isOwner && (
              <Card className="p-6 border-orange-200">
                <div className="flex items-start gap-4">
                  <LogOut className="h-6 w-6 text-orange-600 mt-1" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-text-primary mb-1">Leave Project</h3>
                    <p className="text-sm text-text-secondary mb-4">
                      Remove yourself from this project. You will lose access immediately and need to be re-invited to rejoin.
                    </p>
                    <Button variant="destructive" onClick={handleLeaveProject}>
                      Leave Project
                    </Button>
                  </div>
                </div>
              </Card>
            )}

            {/* Delete Project */}
            {isOwner && (
              <Card className="p-6 border-red-200">
                <div className="flex items-start gap-4">
                  <AlertTriangle className="h-6 w-6 text-red-600 mt-1" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-text-primary mb-1">Delete Project</h3>
                    <p className="text-sm text-text-secondary mb-4">
                      Permanently delete this project and all associated data. This action cannot be undone.
                    </p>
                    <Button variant="destructive" onClick={() => setShowDeleteModal(true)}>
                      Delete Project
                    </Button>
                  </div>
                </div>
              </Card>
            )}
          </div>
        )}
      </div>

      {/* Modals */}
      {isOwner && (
        <>
          <TransferOwnershipModal
            isOpen={showTransferModal}
            onClose={() => setShowTransferModal(false)}
            members={members}
            onTransfer={handleTransferOwnership}
          />
          <DeleteProjectModal
            isOpen={showDeleteModal}
            onClose={() => setShowDeleteModal(false)}
            projectName={project.name}
            onDelete={handleDeleteProject}
          />
        </>
      )}
    </div>
    </TierGate>
  );
}
