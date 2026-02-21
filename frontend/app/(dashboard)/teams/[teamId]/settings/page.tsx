"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  api,
  Team,
  TeamMember,
  TeamInvitation,
  TeamSubscription,
  TeamUpdateRequest,
  TeamInvitationCreateRequest,
  TeamRole,
  parseApiError,
} from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { TeamSettingsGeneral } from "@/components/team/team-settings-general";
import { TeamMembersList } from "@/components/team/team-members-list";
import { TeamInvitationsList } from "@/components/team/team-invitations-list";
import { InviteMemberForm } from "@/components/team/invite-member-form";
import { TeamBillingCard } from "@/components/team/team-billing-card";
import { TransferOwnershipModal } from "@/components/team/transfer-ownership-modal";
import { DeleteTeamModal } from "@/components/team/delete-team-modal";
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

export default function TeamSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const teamId = params.teamId as string;

  const [activeTab, setActiveTab] = useState<Tab>("general");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Data state
  const [team, setTeam] = useState<Team | null>(null);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [invitations, setInvitations] = useState<TeamInvitation[]>([]);
  const [subscription, setSubscription] = useState<TeamSubscription | null>(null);

  // Modal state
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  useEffect(() => {
    loadTeamData();
  }, [teamId]);

  const loadTeamData = async () => {
    try {
      setError("");
      setIsLoading(true);

      const [teamData, membersData, invitationsData, subscriptionData] = await Promise.all([
        api.teams.get(teamId),
        api.teams.members.list(teamId),
        api.teams.invitations.list(teamId),
        api.teams.billing.subscription(teamId),
      ]);

      setTeam(teamData);
      setMembers(membersData);
      setInvitations(invitationsData);
      setSubscription(subscriptionData);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateTeam = async (data: TeamUpdateRequest) => {
    try {
      const updated = await api.teams.update(teamId, data);
      setTeam(updated);
      alert("Team updated successfully!");
    } catch (err) {
      throw new Error(parseApiError(err).message);
    }
  };

  const handleUploadLogo = async (file: File) => {
    try {
      const updated = await api.teams.uploadLogo(teamId, file);
      setTeam(updated);
      alert("Logo uploaded successfully!");
    } catch (err) {
      throw new Error(parseApiError(err).message);
    }
  };

  const handleUpdateRole = async (userId: string, role: TeamRole) => {
    try {
      await api.teams.members.update(teamId, userId, { role });
      await loadTeamData();
      alert("Member role updated successfully!");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleRemoveMember = async (userId: string, memberName: string) => {
    try {
      await api.teams.members.remove(teamId, userId);
      await loadTeamData();
      alert(`${memberName} has been removed from the team`);
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleInviteMember = async (data: TeamInvitationCreateRequest) => {
    try {
      await api.teams.invitations.create(teamId, data);
      await loadTeamData();
      alert(`Invitation sent to ${data.email}`);
    } catch (err) {
      throw new Error(parseApiError(err).message);
    }
  };

  const handleRevokeInvitation = async (invitationId: string) => {
    try {
      await api.teams.invitations.revoke(teamId, invitationId);
      await loadTeamData();
      alert("Invitation revoked");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleResendInvitation = async (invitationId: string) => {
    try {
      await api.teams.invitations.resend(teamId, invitationId);
      alert("Invitation resent");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleUpgrade = async () => {
    try {
      const response = await api.teams.billing.checkout(teamId, "starter_monthly");
      window.location.href = response.checkout_url;
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleManageBilling = async () => {
    try {
      const response = await api.teams.billing.portal(teamId);
      window.open(response.portal_url, "_blank");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleCancelSubscription = async () => {
    if (!confirm("Are you sure you want to cancel your subscription? You will lose access to premium features at the end of your billing period.")) {
      return;
    }

    try {
      await api.teams.billing.cancel(teamId);
      await loadTeamData();
      alert("Subscription cancelled successfully");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleTransferOwnership = async (newOwnerId: string) => {
    try {
      await api.teams.transferOwnership(teamId, newOwnerId);
      router.push("/teams");
      alert("Ownership transferred successfully. You are now an Admin.");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleDeleteTeam = async () => {
    try {
      await api.teams.delete(teamId);
      router.push("/teams");
      alert("Team deleted successfully");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const handleLeaveTeam = async () => {
    if (!confirm("Are you sure you want to leave this team? You will lose access immediately.")) {
      return;
    }

    try {
      await api.teams.leave(teamId);
      router.push("/teams");
      alert("You have left the team");
    } catch (err) {
      alert(parseApiError(err).message);
    }
  };

  const canManageSettings = team && (team.my_role === "owner" || team.my_role === "admin");
  const isOwner = team?.my_role === "owner";

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

  if (error || !team) {
    return (
      <div className="space-y-6">
        <Link href="/teams">
          <Button variant="ghost" size="sm" leftIcon={<ArrowLeft className="h-4 w-4" />}>
            Back to Teams
          </Button>
        </Link>
        <Card className="p-6">
          <div className="text-center py-8">
            <p className="text-red-600 mb-4">{error || "Team not found"}</p>
            <Button onClick={loadTeamData}>Retry</Button>
          </div>
        </Card>
      </div>
    );
  }

  if (!canManageSettings) {
    return (
      <div className="space-y-6">
        <Link href="/teams">
          <Button variant="ghost" size="sm" leftIcon={<ArrowLeft className="h-4 w-4" />}>
            Back to Teams
          </Button>
        </Link>
        <Card className="p-6">
          <div className="text-center py-8">
            <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
            <p className="text-text-primary font-semibold mb-2">Access Denied</p>
            <p className="text-text-muted">
              Only team owners and admins can access settings
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href="/teams">
          <Button variant="ghost" size="sm" leftIcon={<ArrowLeft className="h-4 w-4" />}>
            Back to Teams
          </Button>
        </Link>
        <div className="mt-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">{team.name} Settings</h1>
            <p className="text-text-secondary mt-1">Manage your team configuration</p>
          </div>
          <Badge className={`${team.my_role === "owner" ? "bg-yellow-100 text-yellow-800" : "bg-purple-100 text-purple-800"}`}>
            {team.my_role === "owner" && <Crown className="h-3 w-3 mr-1" />}
            {team.my_role.charAt(0).toUpperCase() + team.my_role.slice(1)}
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
          <TeamSettingsGeneral
            team={team}
            onUpdate={handleUpdateTeam}
            onUploadLogo={handleUploadLogo}
          />
        )}

        {activeTab === "members" && (
          <TeamMembersList
            members={members}
            myRole={team.my_role}
            onUpdateRole={handleUpdateRole}
            onRemove={handleRemoveMember}
          />
        )}

        {activeTab === "invitations" && (
          <div className="space-y-6">
            <InviteMemberForm onInvite={handleInviteMember} />
            <TeamInvitationsList
              invitations={invitations}
              onRevoke={handleRevokeInvitation}
              onResend={handleResendInvitation}
            />
          </div>
        )}

        {activeTab === "billing" && subscription && (
          <TeamBillingCard
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
                      Transfer team ownership to another admin or member. You will become an Admin after transfer.
                    </p>
                    <Button variant="outline" onClick={() => setShowTransferModal(true)}>
                      Transfer Ownership
                    </Button>
                  </div>
                </div>
              </Card>
            )}

            {/* Leave Team */}
            {!isOwner && (
              <Card className="p-6 border-orange-200">
                <div className="flex items-start gap-4">
                  <LogOut className="h-6 w-6 text-orange-600 mt-1" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-text-primary mb-1">Leave Team</h3>
                    <p className="text-sm text-text-secondary mb-4">
                      Remove yourself from this team. You will lose access immediately and need to be re-invited to rejoin.
                    </p>
                    <Button variant="destructive" onClick={handleLeaveTeam}>
                      Leave Team
                    </Button>
                  </div>
                </div>
              </Card>
            )}

            {/* Delete Team */}
            {isOwner && (
              <Card className="p-6 border-red-200">
                <div className="flex items-start gap-4">
                  <AlertTriangle className="h-6 w-6 text-red-600 mt-1" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-text-primary mb-1">Delete Team</h3>
                    <p className="text-sm text-text-secondary mb-4">
                      Permanently delete this team and all associated data. This action cannot be undone.
                    </p>
                    <Button variant="destructive" onClick={() => setShowDeleteModal(true)}>
                      Delete Team
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
          <DeleteTeamModal
            isOpen={showDeleteModal}
            onClose={() => setShowDeleteModal(false)}
            teamName={team.name}
            onDelete={handleDeleteTeam}
          />
        </>
      )}
    </div>
  );
}
