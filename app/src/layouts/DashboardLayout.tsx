import { Outlet, useLocation, useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import {
  LayoutDashboard,
  Building2,
  Bell,
  FileBarChart,
  BrainCircuit,
  Settings,
  LogOut,
  ShieldCheck,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['ciso', 'procurement', 'auditor'] },
  { path: '/vendors', label: 'Vendors', icon: Building2, roles: ['ciso', 'procurement', 'auditor'] },
  { path: '/alerts', label: 'Alerts', icon: Bell, roles: ['ciso', 'procurement', 'auditor'] },
  { path: '/reports', label: 'Reports', icon: FileBarChart, roles: ['ciso', 'procurement'] },
  { path: '/evaluation', label: 'Evaluation', icon: BrainCircuit, roles: ['ciso'] },
  { path: '/settings', label: 'Settings', icon: Settings, roles: ['ciso', 'procurement', 'auditor'] },
];

export default function DashboardLayout() {
  const { user, logout, hasRole, isLoading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-sg-surface">
        <div className="h-8 w-8 animate-spin-slow rounded-full border-2 border-black/10 border-t-sg-primary" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const visibleNavItems = navItems.filter((item) => hasRole(item.roles));

  return (
    <div className="flex h-screen w-full bg-sg-surface-muted">
      {/* Sidebar */}
      <aside className="flex h-full w-sidebar flex-shrink-0 flex-col border-r border-sg-border-subtle bg-white">
        {/* Logo */}
        <div className="flex items-center gap-2 px-4 py-4">
          <ShieldCheck className="h-5 w-5 text-sg-secondary" />
          <span className="font-display text-base font-bold tracking-tight text-sg-text-primary uppercase">VendorSentry</span>
        </div>

        {/* Navigation */}
        <nav className="mt-6 flex flex-1 flex-col gap-1 px-3">
          {visibleNavItems.map((item) => {
            const isActive = location.pathname === item.path ||
              (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
            const Icon = item.icon;

            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`flex items-center gap-3 rounded-sm px-3 py-2.5 text-sm uppercase tracking-wider font-semibold transition-all duration-200 ${
                  isActive
                    ? 'bg-sg-primary text-white'
                    : 'text-sg-text-secondary hover:bg-sg-surface-muted hover:text-sg-text-primary'
                }`}
              >
                <Icon className="h-[18px] w-[18px]" />
                <span>{item.label}</span>
                {item.label === 'Alerts' && (
                  <span className={`ml-auto flex h-5 min-w-[20px] items-center justify-center rounded-sm px-1.5 text-[10px] font-bold ${isActive ? 'bg-white text-sg-primary' : 'bg-sg-primary text-white'}`}>
                    412
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* User section */}
        <div className="border-t border-sg-border-subtle px-3 py-4 bg-white">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center bg-sg-surface-dim text-xs font-bold text-sg-text-primary">
              {user?.name?.split(' ').map((n) => n[0]).join('') || 'U'}
            </div>
            <div className="flex flex-1 flex-col overflow-hidden">
              <span className="truncate text-sm font-bold text-sg-text-primary">{user?.name}</span>
              <span className="truncate text-xs uppercase tracking-wider text-sg-text-secondary">{user?.role}</span>
            </div>
          </div>
          <button
            onClick={() => logout()}
            className="mt-3 flex w-full items-center gap-2 rounded-sm px-3 py-2 text-xs font-semibold uppercase tracking-wider text-sg-text-secondary transition-colors hover:bg-sg-surface-muted hover:text-sg-error"
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">


        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
