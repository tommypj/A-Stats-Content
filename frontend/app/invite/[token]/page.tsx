"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, parseApiError, ProjectInvitationPublic } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Mail, CheckCircle, XCircle, Clock, Building2, Shield, User as UserIcon, Eye, Crown } from "lucide-react";

type InvitationInfo = ProjectInvitationPublic;

const roleIcons = {
  owner: Crown,
  admin: Shield,
  member: UserIcon,
  viewer: Eye,
};

const roleColors = {
  owner: "bg-yellow-100 text-yellow-800",
  admin: "bg-purple-100 text-purple-800",
  member: "bg-blue-100 text-blue-800",
  viewer: "bg-gray-100 text-gray-800",
};

const roleDescriptions = {
  owner: "Full control over project settings and billing",
  admin: "Can manage project members and settings",
  member: "Can create and manage content",
  viewer: "Can view project content only",
};

export default function InviteAcceptPage() {
  const params = useParams();
  const router = useRouter();
  const token = params.token as string;

  const [isLoading, setIsLoading] = useState(true);
  const [isAccepting, setIsAccepting] = useState(false);
  const [error, setError] = useState("");
  const [invitation, setInvitation] = useState<InvitationInfo | null>(null);
  const { isAuthenticated } = useAuthStore();
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    loadInvitation();
  }, [token]);

  // Mirror Zustand isAuthenticated into local isLoggedIn state so the
  // invite UI reflects the correct login state without reading localStorage.
  useEffect(() => {
    setIsLoggedIn(isAuthenticated);
  }, [isAuthenticated]);

  const loadInvitation = async () => {
    try {
      setError("");
      const data = await api.projects.invitations.getByToken(token);
      setInvitation(data);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAccept = async () => {
    if (!isLoggedIn) {
      // Redirect to login with return URL
      router.push(`/login?redirect=${encodeURIComponent(`/invite/${token}`)}`);
      return;
    }

    setIsAccepting(true);
    try {
      await api.projects.invitations.accept(token);
      router.push("/projects");
      toast.success("Invitation accepted! Welcome to the project.");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setIsAccepting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-surface-secondary flex items-center justify-center p-4">
        <Card className="w-full max-w-md p-8">
          <div className="text-center space-y-4">
            <Skeleton className="h-16 w-16 rounded-full mx-auto" />
            <Skeleton className="h-6 w-3/4 mx-auto" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3 mx-auto" />
          </div>
        </Card>
      </div>
    );
  }

  if (error || !invitation) {
    return (
      <div className="min-h-screen bg-surface-secondary flex items-center justify-center p-4">
        <Card className="w-full max-w-md p-8">
          <div className="text-center space-y-4">
            <div className="h-16 w-16 rounded-full bg-red-100 flex items-center justify-center mx-auto">
              <XCircle className="h-8 w-8 text-red-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-text-primary mb-2">
                Invalid Invitation
              </h1>
              <p className="text-text-muted">
                {error || "This invitation link is invalid or has expired."}
              </p>
            </div>
            <Link href="/">
              <Button>Go to Homepage</Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  const RoleIcon = roleIcons[invitation.role];
  const isExpired = invitation.is_expired;
  const isAlreadyMember = invitation.is_already_member;
  const canAccept = !isExpired && !isAlreadyMember;

  return (
    <div className="min-h-screen bg-surface-secondary flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        {/* Header */}
        <div className="p-8 text-center border-b border-surface-tertiary">
          <div className="h-16 w-16 rounded-full bg-primary-100 flex items-center justify-center mx-auto mb-4">
            {invitation.project_logo_url ? (
              <img
                src={invitation.project_logo_url}
                alt={invitation.project_name}
                className="h-full w-full rounded-full object-cover"
              />
            ) : (
              <Building2 className="h-8 w-8 text-primary-600" />
            )}
          </div>
          <h1 className="text-2xl font-bold text-text-primary mb-2">
            Project Invitation
          </h1>
          <p className="text-text-muted">
            You've been invited to join a project
          </p>
        </div>

        {/* Content */}
        <div className="p-8 space-y-6">
          {/* Team Info */}
          <div className="text-center">
            <p className="text-text-secondary mb-2">You're invited to join</p>
            <p className="text-2xl font-bold text-text-primary mb-4">
              {invitation.project_name}
            </p>
          </div>

          {/* Role Badge */}
          <div className="flex justify-center">
            <Badge className={`${roleColors[invitation.role]} text-base py-1.5 px-4`}>
              <RoleIcon className="h-4 w-4 mr-2" />
              {invitation.role.charAt(0).toUpperCase() + invitation.role.slice(1)}
            </Badge>
          </div>

          {/* Role Description */}
          <div className="p-4 rounded-lg bg-primary-50 border border-primary-200">
            <p className="text-sm text-primary-800 text-center">
              {roleDescriptions[invitation.role]}
            </p>
          </div>

          {/* Inviter Info */}
          <div className="flex items-center justify-center gap-3 p-4 rounded-lg bg-surface-secondary">
            <Mail className="h-5 w-5 text-text-muted" />
            <div className="text-left">
              <p className="text-sm text-text-secondary">Invited by</p>
              <p className="font-medium text-text-primary">{invitation.inviter_name}</p>
            </div>
          </div>

          {/* Status Messages */}
          {isExpired && (
            <div className="p-4 rounded-lg bg-yellow-50 border border-yellow-200">
              <div className="flex items-start gap-3">
                <Clock className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div>
                  <p className="font-medium text-yellow-900">Invitation Expired</p>
                  <p className="text-sm text-yellow-800 mt-1">
                    This invitation expired on {new Date(invitation.expires_at).toLocaleDateString()}.
                    Please contact the project admin for a new invitation.
                  </p>
                </div>
              </div>
            </div>
          )}

          {isAlreadyMember && (
            <div className="p-4 rounded-lg bg-green-50 border border-green-200">
              <div className="flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                <div>
                  <p className="font-medium text-green-900">Already a Member</p>
                  <p className="text-sm text-green-800 mt-1">
                    You're already a member of this project.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="space-y-3">
            {canAccept && (
              <>
                {isLoggedIn ? (
                  <Button
                    onClick={handleAccept}
                    isLoading={isAccepting}
                    className="w-full"
                  >
                    Accept Invitation
                  </Button>
                ) : (
                  <>
                    <Link href={`/login?redirect=${encodeURIComponent(`/invite/${token}`)}`}>
                      <Button className="w-full">Sign In to Accept</Button>
                    </Link>
                    <Link href={`/register?redirect=${encodeURIComponent(`/invite/${token}`)}`}>
                      <Button variant="outline" className="w-full">
                        Create Account
                      </Button>
                    </Link>
                  </>
                )}
              </>
            )}

            {!canAccept && (
              <Link href="/">
                <Button variant="outline" className="w-full">
                  Go to Homepage
                </Button>
              </Link>
            )}
          </div>

          {/* Expiry Info */}
          {canAccept && (
            <p className="text-xs text-text-muted text-center">
              This invitation expires on {new Date(invitation.expires_at).toLocaleDateString()}
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}
