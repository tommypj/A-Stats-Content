"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  api,
  Project,
  ProjectMember,
  ProjectInvitation,
  ProjectSubscription,
  ProjectUpdateRequest,
  ProjectInvitationCreateRequest,
  ProjectRole,
  parseApiError,
} from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ProjectSettingsGeneral } from "@/components/project/project-settings-general";
import { ProjectMembersList } from "@/components/project/project-members-list";
import { ProjectInvitationsList } from "@/components/project/project-invitations-list";
import { InviteMemberForm } from "@/components/project/invite-member-form";
import { ProjectBillingCard } from "@/components/project/project-billing-card";
import { TransferOwnershipModal } from "@/components/project/transfer-ownership-modal";
import { DeleteProjectModal } from "@/components/project/delete-project-modal";
import {
  ArrowLeft,
  Settings,
  Users,
  Mail,
  CreditCard,
  AlertTriangle,
  Crown,
  LogOut,
} from "lucide-react";

type Tab = "general" | "members" | "invitations" | "billing" | "danger";

const tabs = [
  { id: "general" as Tab, label: "General", icon: Settings },
  { id: "members" as Tab, label: "Members", icon: Users },
  { id: "invitations" as Tab, label: "Invitations", icon: Mail },
  { id: "billing" as Tab, label: "Billing", icon: CreditCard },
  { id: "danger" as Tab, label: "Danger Zone", icon: AlertTriangle },
];

export default function ProjectSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [activeTab, setActiveTab] = useState<Tab>("general");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Data state
  const [project, setProject] = useState<Project | null>(null);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [invitations, setInvitations] = useState<ProjectInvitation[]>([]);
  const [subscription, setSubscription] = useState<ProjectSubscription | null>(null);

  // Modal state
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ action: () => void; title: string; message: string; confirmLabel?: string; variant?: "danger" | "warning" | "default" } | null>(null);

  useEffect(() => {
    loadProjectData();
  }, [projectId]);

  const loadProjectData = async () => {
    try {
      setError("");
      setIsLoading(true);

      const [projectData, membersData, invitationsData, subscriptionData] = await Promise.all([
        api.projects.get(projectId),
        api.projects.members.list(projectId),
        api.projects.invitations.list(projectId),
        api.projects.billing.subscription(projectId),
      ]);

      setProject(projectData);
      setMembers(membersData);
      setInvitations(invitationsData);
      setSubscription(subscriptionData);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateProject = async (data: ProjectUpdateRequest) => {
    try {
      const updated = await api.projects.update(projectId, data);
      setProject(updated);
      alert("Project updated successfully!");
    } catch (err) {
      throw new Error(parseApiError(err).message);
    }
  };

  const handleUploadLogo = async (file: File) => {
    try {
      const updated = await api.projects.uploadLogo(projectId, file);
      setProject(updated);
      alert("Logo uploaded successfully!");
    } catch (err) {
      throw new Error(parseApiError(err).message);
    }
  };

  const handleUpdateRole = async (userId: string, role: ProjectRole) => {
    try {
      await api.projects.members.update(projectId, userId, { role });
      await loadProjectData();
      alert("Member role updated successfully!");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleRemoveMember = async (userId: string, memberName: string) => {
    try {
      await api.projects.members.remove(projectId, userId);
      await loadProjectData();
      alert(`${memberName} has been removed from the project`);
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleInviteMember = async (data: ProjectInvitationCreateRequest) => {
    try {
      await api.projects.invitations.create(projectId, data);
      await loadProjectData();
      alert(`Invitation sent to ${data.email}`);
    } catch (err) {
      throw new Error(parseApiError(err).message);
    }
  };

  const handleRevokeInvitation = async (invitationId: string) => {
    try {
      await api.projects.invitations.revoke(projectId, invitationId);
      await loadProjectData();
      alert("Invitation revoked");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleResendInvitation = async (invitationId: string) => {
    try {
      await api.projects.invitations.resend(projectId, invitationId);
      alert("Invitation resent");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleUpgrade = async () => {
    try {
      const response = await api.projects.billing.checkout(projectId, "starter_monthly");
      window.location.href = response.checkout_url;
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleManageBilling = async () => {
    try {
      const response = await api.projects.billing.portal(projectId);
      window.open(response.portal_url, "_blank");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleCancelSubscription = () => {
    setConfirmAction({
      action: async () => {
        try {
          await api.projects.billing.cancel(projectId);
          await loadProjectData();
          alert("Subscription cancelled successfully");
        } catch (err) {
          alert(parseApiError(err).message);
        }
      },
      title: "Cancel Subscription",
      message: "Are you sure you want to cancel your subscription? You will lose access to premium features at the end of your billing period.",
      confirmLabel: "Cancel Subscription",
      variant: "warning",
    });
  };

  const handleTransferOwnership = async (newOwnerId: string) => {
    try {
      await api.projects.transferOwnership(projectId, newOwnerId);
      router.push("/projects");
      alert("Ownership transferred successfully. You are now an Admin.");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleDeleteProject = async () => {
    try {
      await api.projects.delete(projectId);
      router.push("/projects");
      alert("Project deleted successfully");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleLeaveProject = () => {
    setConfirmAction({
      action: async () => {
        try {
          await api.projects.leave(projectId);
          router.push("/projects");
          alert("You have left the project");
        } catch (err) {
          alert(parseApiError(err).message);
        }
      },
      title: "Leave Project",
      message: "Are you sure you want to leave this project? You will lose access immediately.",
      confirmLabel: "Leave Project",
      variant: "warning",
    });
  };

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
            <Button onClick={loadProjectData}>Retry</Button>
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

        {activeTab === "billing" && subscription && (
          <ProjectBillingCard
            subscription={subscription}
            onUpgrade={handleUpgrade}
            onManageBilling={handleManageBilling}
            onCancel={handleCancelSubscription}
          />
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
  );
}
