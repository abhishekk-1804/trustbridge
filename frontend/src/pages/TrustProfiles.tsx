import * as React from 'react';
import { useUsers } from '@/api';
import { cn } from '@/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, Column } from '@/components/ui/Table';
import { Users, Search, ChevronRight, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

export function TrustProfiles() {
  const { data: usersData, isLoading, error: usersError } = useUsers(50);
  const [search, setSearch] = React.useState('');

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-text">Trust Profiles</h1>
            <p className="text-text-muted mt-1">Search and view trust profiles</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="h-40" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (usersError) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-text">Trust Profiles</h1>
            <p className="text-text-muted mt-1">Search and view trust profiles</p>
          </div>
        </div>
        <Card className="border-border/50">
          <CardContent className="py-8 text-center">
            <AlertCircle className="w-12 h-12 text-text-danger mx-auto mb-4" />
            <h3 className="text-lg font-medium text-text">Failed to load users</h3>
            <p className="text-text-muted mt-2">Unable to load user data. Please try again later.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const filteredUsers = usersData?.users.filter((u) =>
    u.name.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase())
  ) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text">Trust Profiles</h1>
          <p className="text-text-muted mt-1">Search and view trust profiles</p>
        </div>
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
          <input
            type="text"
            placeholder="Search users..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10"
          />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {filteredUsers.length === 0 ? (
            <div className="text-center py-12">
              <Users className="w-12 h-12 text-text-muted mx-auto mb-4" />
              <h3 className="text-lg font-medium text-text">No users found</h3>
              <p className="text-text-muted mt-2">
                {search ? 'Try adjusting your search' : 'No users in the system'}
              </p>
            </div>
          ) : (
            <Table
              data={filteredUsers}
              columns={[
                { key: 'name', header: 'Identity', render: (row) => (
                  <div>
                    <Link to={`/trust/${row.id}`} className="font-medium text-text hover:text-primary">
                      {row.name}
                    </Link>
                    <p className="text-xs text-text-muted">{row.email}</p>
                  </div>
                )},
                { key: 'role', header: 'Role', render: (row) => <Badge variant="info">{row.role.replace('_', ' ')}</Badge> },
                { key: 'verified', header: 'Verification', render: (row) => (
                  <Badge variant={row.is_verified ? 'success' : 'neutral'}>
                    {row.is_verified ? 'Verified' : 'Pending'}
                  </Badge>
                )},
                { key: 'actions', header: '', render: (row) => (
                  <Link to={`/trust/${row.id}`} className="text-primary hover:underline flex items-center gap-1 text-sm">
                    View <ChevronRight className="w-4 h-4" />
                  </Link>
                )},
              ]}
              keyField="id"
              emptyMessage="No users found"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}