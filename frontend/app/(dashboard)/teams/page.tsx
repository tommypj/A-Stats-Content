"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, Team, parseApiError } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Plus,
  Users,
  Crown,
  Shield,
  User as UserIcon,
  Eye,
  Building2,
  ArrowRight,
  Loader2,
} from "lucide-react";
import Image from "next/image";

const tierColors = {
  free: "bg-gray-100 text-gray-800",
  starter: "bg-blue-100 text-blue-800",
  professional: "bg-purple-100 text-purple-800",
  enterprise: "bg-orange-100 text-orange-800",
};

const roleIcons = {
  owner: Crown,
  admin: Shield,
  member: UserIcon,
  viewer: Eye,
};

const roleColors = {
  owner: "text-yellow-600",
  admin: "text-purple-600",
  member: "text-blue-600",
  viewer: "text-gray-600",
};

export default function TeamsPage() {
  const router = useRouter();
  const [teams, setTeams] = useState<Team[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [switchingTeam, setSwitchingTeam] = useState<string | null>(null);

  useEffect(() => {
    loadTeams();
  }, []);

  const loadTeams = async () => {
    try {
      setError("");
      const data = await api.teams.list();
      setTeams(data);
    } catch (err) {
      setError(parseApiError(err).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSwitchTeam = async (teamId: string | null) => {
    setSwitchingTeam(teamId || "personal");
    try {
      await api.teams.switch(teamId);
      // Redirect to dashboard after switching
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      alert(parseApiError(err).message);
      setSwitchingTeam(null);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">Teams</h1>
            <p className="text-text-secondary mt-1">Manage your team workspaces</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-6">
              <Skeleton className="h-12 w-12 rounded-xl mb-4" />
              <Skeleton className="h-6 w-3/4 mb-2" />
              <Skeleton className="h-4 w-1/2" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">Teams</h1>
            <p className="text-text-secondary mt-1">Manage your team workspaces</p>
          </div>
        </div>

        <Card className="p-6">
          <div className="text-center py-8">
            <p className="text-red-600 mb-4">{error}</p>
            <Button onClick={loadTeams}>Retry</Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Teams</h1>
          <p className="text-text-secondary mt-1">
            Switch between workspaces or create a new team
          </p>
        </div>
        <Link href="/teams/new">
          <Button leftIcon={<Plus className="h-4 w-4" />}>Create Team</Button>
        </Link>
      </div>

      {/* Personal Workspace Card */}
      <Card className="p-6 hover:shadow-lg transition-shadow border-2 border-primary-200">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4 flex-1">
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center">
              <UserIcon className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-text-primary text-lg">
                Personal Workspace
              </h3>
              <p className="text-sm text-text-muted mt-1">
                Your private workspace for individual projects
              </p>
              <div className="flex items-center gap-3 mt-3">
                <Badge className="bg-primary-100 text-primary-800">Personal</Badge>
              </div>
            </div>
          </div>
          <Button
            variant="outline"
            onClick={() => handleSwitchTeam(null)}
            isLoading={switchingTeam === "personal"}
            disabled={switchingTeam !== null}
            rightIcon={<ArrowRight className="h-4 w-4" />}
          >
            Switch
          </Button>
        </div>
      </Card>

      {/* Teams Grid */}
      {teams.length > 0 && (
        <>
          <div className="flex items-center gap-2 pt-4">
            <Building2 className="h-5 w-5 text-text-secondary" />
            <h2 className="text-lg font-semibold text-text-primary">Your Teams</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {teams.map((team) => {
              const RoleIcon = roleIcons[team.my_role];
              const isLoading = switchingTeam === team.id;

              return (
                <Card
                  key={team.id}
                  className="p-6 hover:shadow-lg transition-all hover:border-primary-300 cursor-pointer group"
                >
                  <div className="space-y-4">
                    {/* Team Logo & Name */}
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3 flex-1">
                        <div className="h-12 w-12 rounded-xl bg-surface-secondary flex items-center justify-center overflow-hidden border border-surface-tertiary">
                          {team.logo_url ? (
                            <Image
                              src={team.logo_url}
                              alt={team.name}
                              width={48}
                              height={48}
                              className="object-cover w-full h-full"
                            />
                          ) : (
                            <Building2 className="h-6 w-6 text-text-muted" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-text-primary truncate">
                            {team.name}
                          </h3>
                          {team.description && (
                            <p className="text-sm text-text-muted line-clamp-2 mt-1">
                              {team.description}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Badges */}
                    <div className="flex items-center gap-2">
                      <Badge className={tierColors[team.subscription_tier]}>
                        {team.subscription_tier.charAt(0).toUpperCase() +
                          team.subscription_tier.slice(1)}
                      </Badge>
                      <div className="flex items-center gap-1 text-sm text-text-muted">
                        <Users className="h-3 w-3" />
                        <span>{team.member_count}</span>
                      </div>
                    </div>

                    {/* Role & Actions */}
                    <div className="flex items-center justify-between pt-2 border-t border-surface-tertiary">
                      <div className="flex items-center gap-1.5">
                        <RoleIcon className={`h-4 w-4 ${roleColors[team.my_role]}`} />
                        <span className="text-sm font-medium text-text-secondary capitalize">
                          {team.my_role}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {(team.my_role === "owner" || team.my_role === "admin") && (
                          <Link href={`/teams/${team.id}/settings`}>
                            <Button variant="ghost" size="sm">
                              Settings
                            </Button>
                          </Link>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleSwitchTeam(team.id)}
                          isLoading={isLoading}
                          disabled={switchingTeam !== null}
                        >
                          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Switch"}
                        </Button>
                      </div>
                    </div>
                  </div>
                </Card>
              );
            })}

            {/* Create New Team Card */}
            <Link href="/teams/new">
              <Card className="p-6 h-full hover:shadow-lg transition-all hover:border-primary-300 border-2 border-dashed border-surface-tertiary cursor-pointer group">
                <div className="h-full flex flex-col items-center justify-center text-center space-y-3">
                  <div className="h-12 w-12 rounded-xl bg-primary-50 flex items-center justify-center group-hover:bg-primary-100 transition-colors">
                    <Plus className="h-6 w-6 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-text-primary">Create New Team</h3>
                    <p className="text-sm text-text-muted mt-1">
                      Start collaborating with your team
                    </p>
                  </div>
                </div>
              </Card>
            </Link>
          </div>
        </>
      )}

      {teams.length === 0 && (
        <Card className="p-12">
          <div className="text-center">
            <div className="h-16 w-16 rounded-full bg-primary-50 flex items-center justify-center mx-auto mb-4">
              <Building2 className="h-8 w-8 text-primary-600" />
            </div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              No teams yet
            </h3>
            <p className="text-text-muted mb-6">
              Create your first team to start collaborating with others
            </p>
            <Link href="/teams/new">
              <Button leftIcon={<Plus className="h-4 w-4" />}>Create Your First Team</Button>
            </Link>
          </div>
        </Card>
      )}
    </div>
  );
}
