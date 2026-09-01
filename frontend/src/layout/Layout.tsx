import * as React from 'react';
import { Link, useLocation, NavLink } from 'react-router-dom';
import { cn } from '@/utils';
import {
  LayoutDashboard,
  Users,
  ShieldAlert,
  CreditCard,
  Search,
  FileText,
  FlaskConical,
  Code,
  Shield,
  Menu,
  X,
  ChevronDown,
  Bell,
  Settings,
  LogOut,
  User,
  Bot,
} from 'lucide-react';

const navigation = [
  { name: 'Command Center', href: '/', icon: LayoutDashboard },
  { name: 'Trust Profiles', href: '/trust', icon: Users },
  { name: 'Risk Intelligence', href: '/risk', icon: ShieldAlert },
  { name: 'Payments', href: '/payments', icon: CreditCard },
  { name: 'AI Copilot', href: '/copilot', icon: Bot },
  { name: 'Verifications', href: '/verification', icon: Shield },
  { name: 'Investigations', href: '/investigations', icon: Search },
  { name: 'Model Lab', href: '/model-lab', icon: FlaskConical },
  { name: 'Developers', href: '/developers', icon: Code },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [userMenuOpen, setUserMenuOpen] = React.useState(false);

  const isActivePath = (href: string) => {
    if (href === '/') return location.pathname === '/';
    return location.pathname.startsWith(href);
  };

  return (
    <div className="min-h-screen bg-bg flex">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-bg-card border-r border-border flex flex-col transition-transform duration-200 lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        aria-label="Main navigation"
      >
        <div className="flex h-16 items-center justify-between px-4 border-b border-border">
          <Link to="/" className="flex items-center gap-2" aria-label="TrustBridge Home">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Shield className="w-5 h-5 text-black" />
            </div>
            <span className="font-semibold text-text">TrustBridge</span>
          </Link>
          <button
            className="lg:hidden p-2 text-text-muted hover:text-text transition-colors"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 py-4 overflow-y-auto" aria-label="Main navigation">
          <ul className="px-2 space-y-1" role="list">
            {navigation.map((item) => {
              const Icon = item.icon;
              const active = isActivePath(item.href);
              return (
                <li key={item.name}>
                  <NavLink
                    to={item.href}
                    end={item.href === '/'}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-primary/10 text-primary border-l-2 border-primary'
                          : 'text-text-muted hover:text-text hover:bg-bg-elevated'
                      )
                    }
                  >
                    <Icon className={cn('w-5 h-5 flex-shrink-0', active ? 'text-primary' : 'text-text-muted')} aria-hidden="true" />
                    {item.name}
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="p-4 border-t border-border">
          <Link
            to="/verification"
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-text-muted hover:text-text hover:bg-bg-elevated transition-colors"
          >
            <Shield className="w-5 h-5" aria-hidden="true" />
            Verifications
          </Link>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 lg:ml-64 min-w-0 flex flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-30 h-16 bg-bg/80 backdrop-blur-sm border-b border-border flex items-center justify-between px-4 lg:px-6">
          <button
            className="lg:hidden p-2 text-text-muted hover:text-text transition-colors"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <Menu className="w-6 h-6" />
          </button>

          <div className="flex-1 lg:hidden" />

          <div className="flex items-center gap-4">
            {/* Notifications */}
            <button className="relative p-2 text-text-muted hover:text-text transition-colors rounded-lg hover:bg-bg-elevated" aria-label="Notifications">
              <Bell className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-danger text-[10px] font-semibold rounded-full flex items-center justify-center">
                3
              </span>
            </button>

            {/* User menu */}
            <div className="relative">
              <button
                className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-bg-elevated transition-colors"
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                aria-expanded={userMenuOpen}
                aria-haspopup="true"
                aria-label="User menu"
              >
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                  <User className="w-4 h-4 text-primary" />
                </div>
                <div className="hidden sm:block text-left">
                  <p className="text-xs font-medium text-text">Admin User</p>
                  <p className="text-[11px] text-text-muted">Administrator</p>
                </div>
                <ChevronDown className="w-4 h-4 text-text-muted" />
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-bg-card border border-border rounded-lg shadow-xl py-1 z-50 animate-slide-in">
                  <div className="px-3 py-2 border-b border-border">
                    <p className="text-sm font-medium text-text">Admin User</p>
                    <p className="text-xs text-text-muted">administrator@trustbridge.demo</p>
                  </div>
                  <NavLink
                    to="/developers"
                    className="flex items-center gap-2 px-3 py-2 text-sm text-text-muted hover:text-text hover:bg-bg-elevated"
                    onClick={() => setUserMenuOpen(false)}
                  >
                    <Settings className="w-4 h-4" />
                    Settings
                  </NavLink>
                  <button className="flex w-full items-center gap-2 px-3 py-2 text-sm text-danger hover:bg-danger/10">
                    <LogOut className="w-4 h-4" />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Main content area */}
        <main className="flex-1 p-4 lg:p-6 overflow-y-auto">
          <div className="container">{children}</div>
        </main>
      </div>
    </div>
  );
}