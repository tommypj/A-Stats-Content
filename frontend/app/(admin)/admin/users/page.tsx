"use client";

import { useState, useEffect } from "react";
import { api, AdminUserDetail, AdminUserQueryParams } from "@/lib/api";
import { UserTable } from "@/components/admin/user-table";
import { UserEditModal } from "@/components/admin/user-edit-modal";
import { SuspendUserModal } from "@/components/admin/suspend-user-modal";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Search, Filter, Ban, ChevronLeft, ChevronRight } from "lucide-react";
import { parseApiError } from "@/lib/api";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);

  // Filters
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [tierFilter, setTierFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Selection
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set());

  // Modals
  const [editingUser, setEditingUser] = useState<AdminUserDetail | null>(null);
  const [suspendingUser, setSuspendingUser] = useState<AdminUserDetail | null>(
    null
  );
  const [bulkSuspending, setBulkSuspending] = useState(false);

  const pageSize = 20;

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: AdminUserQueryParams = {
        page,
        page_size: pageSize,
      };

      if (search) params.search = search;
      if (roleFilter !== "all") params.tier = roleFilter;
      if (tierFilter !== "all") params.tier = tierFilter;
      if (statusFilter === "suspended") params.status = "suspended";
      if (statusFilter === "active") params.status = "active";

      const response = await api.admin.users.list(params);
      setUsers(response.users);
      setTotal(response.total);
      setPages(response.total_pages);
    } catch (err) {
      const apiError = parseApiError(err);
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [page, search, roleFilter, tierFilter, statusFilter]);

  const handleSelectUser = (userId: string, selected: boolean) => {
    const newSelected = new Set(selectedUsers);
    if (selected) {
      newSelected.add(userId);
    } else {
      newSelected.delete(userId);
    }
    setSelectedUsers(newSelected);
  };

  const handleSelectAll = (selected: boolean) => {
    if (selected) {
      setSelectedUsers(new Set(users.map((u) => u.id)));
    } else {
      setSelectedUsers(new Set());
    }
  };

  const handleEdit = (user: AdminUserDetail) => {
    setEditingUser(user);
  };

  const handleSuspend = (user: AdminUserDetail) => {
    setSuspendingUser(user);
  };

  const handleUnsuspend = async (user: AdminUserDetail) => {
    try {
      await api.admin.users.unsuspend(user.id);
      await fetchUsers();
    } catch (err) {
      const apiError = parseApiError(err);
      alert(`Failed to unsuspend user: ${apiError.message}`);
    }
  };

  const handleBulkSuspend = () => {
    setBulkSuspending(true);
  };

  const handleUserUpdated = () => {
    setEditingUser(null);
    setSuspendingUser(null);
    setBulkSuspending(false);
    setSelectedUsers(new Set());
    fetchUsers();
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">
            User Management
          </h1>
          <p className="text-text-muted mt-1">
            Manage users, roles, and subscriptions
          </p>
        </div>
      </div>

      <Card className="p-6">
        <div className="space-y-4">
          {/* Search and Filters */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div className="md:col-span-2">
              <Input
                placeholder="Search by name or email..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                leftIcon={<Search className="h-4 w-4" />}
              />
            </div>
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-surface-tertiary bg-surface px-4 py-2.5 text-sm text-text-primary focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            >
              <option value="all">All Roles</option>
              <option value="user">User</option>
              <option value="admin">Admin</option>
              <option value="super_admin">Super Admin</option>
            </select>
            <select
              value={tierFilter}
              onChange={(e) => {
                setTierFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-surface-tertiary bg-surface px-4 py-2.5 text-sm text-text-primary focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            >
              <option value="all">All Tiers</option>
              <option value="free">Free</option>
              <option value="starter">Starter</option>
              <option value="professional">Professional</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="rounded-xl border border-surface-tertiary bg-surface px-4 py-2.5 text-sm text-text-primary focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="suspended">Suspended</option>
              </select>

              <div className="text-sm text-text-muted">
                {total} user{total !== 1 ? "s" : ""} found
              </div>
            </div>

            {selectedUsers.size > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-text-muted">
                  {selectedUsers.size} selected
                </span>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={handleBulkSuspend}
                  leftIcon={<Ban className="h-4 w-4" />}
                >
                  Bulk Suspend
                </Button>
              </div>
            )}
          </div>
        </div>
      </Card>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          {error}
        </div>
      )}

      <Card>
        {loading ? (
          <div className="p-12 text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-500 border-r-transparent"></div>
            <p className="mt-4 text-text-muted">Loading users...</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <UserTable
                users={users}
                onEdit={handleEdit}
                onSuspend={handleSuspend}
                onUnsuspend={handleUnsuspend}
                selectedUsers={selectedUsers}
                onSelectUser={handleSelectUser}
                onSelectAll={handleSelectAll}
              />
            </div>

            {/* Pagination */}
            {pages > 1 && (
              <div className="p-4 border-t border-surface-tertiary flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm text-text-muted">
                  Page {page} of {pages}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    leftIcon={<ChevronLeft className="h-4 w-4" />}
                  >
                    Previous
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setPage((p) => Math.min(pages, p + 1))}
                    disabled={page === pages}
                    rightIcon={<ChevronRight className="h-4 w-4" />}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>

      {/* Modals */}
      {editingUser && (
        <UserEditModal
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onSuccess={handleUserUpdated}
        />
      )}

      {suspendingUser && (
        <SuspendUserModal
          user={suspendingUser}
          onClose={() => setSuspendingUser(null)}
          onSuccess={handleUserUpdated}
        />
      )}

      {bulkSuspending && (
        <SuspendUserModal
          userIds={Array.from(selectedUsers)}
          onClose={() => setBulkSuspending(false)}
          onSuccess={handleUserUpdated}
        />
      )}
    </div>
  );
}
