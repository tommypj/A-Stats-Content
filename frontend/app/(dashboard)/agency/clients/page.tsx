"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Users,
  Plus,
  ExternalLink,
  Shield,
  Trash2,
  Check,
  Search,
} from "lucide-react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, parseApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TierGate } from "@/components/ui/tier-gate";

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

export default function AgencyClientsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");

  // Add client modal
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({
    client_name: "",
    client_email: "",
    project_id: "",
  });

  // --- React Query hooks ---

  const { data: clientsData, isLoading: clientsLoading } = useQuery({
    queryKey: ["agency", "clients"],
    queryFn: () => api.agency.clients(),
    staleTime: 30_000,
  });

  const { data: projects = [], isLoading: projectsLoading } = useQuery({
    queryKey: ["projects", "list"],
    queryFn: () => api.projects.list(),
    staleTime: 30_000,
  });

  const addClientMutation = useMutation({
    mutationFn: (data: { client_name: string; client_email: string; project_id: string }) =>
      api.agency.createClient(data),
    onSuccess: () => {
      toast.success("Client workspace created");
      setShowAdd(false);
      setAddForm({ client_name: "", client_email: "", project_id: "" });
      queryClient.invalidateQueries({ queryKey: ["agency", "clients"] });
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const deleteClientMutation = useMutation({
    mutationFn: (id: string) => api.agency.deleteClient(id),
    onSuccess: () => {
      toast.success("Client workspace deleted");
      queryClient.invalidateQueries({ queryKey: ["agency", "clients"] });
    },
    onError: (err) => {
      toast.error(parseApiError(err).message);
    },
  });

  const handleAddClient = () => {
    if (!addForm.client_name || !addForm.project_id) {
      toast.error("Client name and project are required");
      return;
    }
    addClientMutation.mutate(addForm);
  };

  const handleDelete = (id: string) => {
    if (!confirm("Delete this client workspace? This cannot be undone.")) return;
    deleteClientMutation.mutate(id);
  };

  const clients = clientsData?.items ?? [];
  const loading = clientsLoading || projectsLoading;

  const filtered = clients.filter(
    (c) =>
      c.client_name.toLowerCase().includes(search.toLowerCase()) ||
      (c.client_email || "").toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  return (
    <TierGate minimum="enterprise" feature="Agency Mode">
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Client Workspaces</h1>
          <p className="text-text-secondary mt-1">
            Manage your agency client workspaces and portal access.
          </p>
        </div>
        <Button variant="primary" onClick={() => setShowAdd(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Client
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
        <input
          type="text"
          placeholder="Search clients..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className={`${INPUT_CLASS} pl-9`}
        />
      </div>

      {/* Client Grid */}
      {filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Users className="h-12 w-12 text-text-muted mx-auto mb-4" />
            <p className="text-text-secondary">
              {clients.length === 0
                ? "No client workspaces yet. Add your first client to get started."
                : "No clients match your search."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((client) => (
            <Card key={client.id} className="hover:border-primary-300 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-base">{client.client_name}</CardTitle>
                  <PortalStatusBadge enabled={client.is_portal_enabled} />
                </div>
                {client.client_email && (
                  <p className="text-sm text-text-muted">{client.client_email}</p>
                )}
              </CardHeader>
              <CardContent className="pt-0 space-y-3">
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(client.allowed_features || {})
                    .filter(([, v]) => v)
                    .map(([f]) => (
                    <span
                      key={f}
                      className="px-2 py-0.5 rounded text-xs bg-primary-100 text-primary-700 font-medium"
                    >
                      {f}
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-2 pt-2">
                  <Link href={`/agency/clients/${client.id}`} className="flex-1">
                    <Button variant="outline" className="w-full" size="sm">
                      <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                      Manage
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(client.id)}
                  >
                    <Trash2 className="h-3.5 w-3.5 text-red-500" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add Client Modal */}
      <Dialog
        isOpen={showAdd}
        onClose={() => setShowAdd(false)}
        title="Add Client Workspace"
      >
        <div className="space-y-4">
          <div>
            <label htmlFor="client-name" className="block text-sm font-medium text-text-secondary mb-1">
              Client Name *
            </label>
            <input
              id="client-name"
              type="text"
              value={addForm.client_name}
              onChange={(e) =>
                setAddForm({ ...addForm, client_name: e.target.value })
              }
              className={INPUT_CLASS}
              placeholder="Acme Corp"
            />
          </div>
          <div>
            <label htmlFor="client-email" className="block text-sm font-medium text-text-secondary mb-1">
              Client Email
            </label>
            <input
              id="client-email"
              type="email"
              value={addForm.client_email}
              onChange={(e) =>
                setAddForm({ ...addForm, client_email: e.target.value })
              }
              className={INPUT_CLASS}
              placeholder="client@example.com"
            />
          </div>
          <div>
            <label htmlFor="project" className="block text-sm font-medium text-text-secondary mb-1">
              Project *
            </label>
            <select
              id="project"
              value={addForm.project_id}
              onChange={(e) =>
                setAddForm({ ...addForm, project_id: e.target.value })
              }
              className={INPUT_CLASS}
            >
              <option value="">Select project...</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="ghost" onClick={() => setShowAdd(false)}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleAddClient}
            disabled={addClientMutation.isPending}
          >
            {addClientMutation.isPending ? "Creating..." : "Create Workspace"}
          </Button>
        </div>
      </Dialog>
    </div>
    </TierGate>
  );
}
