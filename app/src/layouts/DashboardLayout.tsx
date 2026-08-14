import { useState } from 'react';
import { Outlet, useLocation, useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import {
  LayoutDashboard,
  Building2,
  Bell,
  FileBarChart,
  Settings,
  LogOut,
  ShieldCheck,
  Sparkles,
  Menu,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import CopilotPanel from '@/components/Copilot/CopilotPanel';
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from '@/components/ui/sheet';
import { useQuery } from '@tanstack/react-query';
import { alertsApi } from '@/api';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['ciso', 'procurement', 'auditor'] },
  { path: '/vendors', label: 'Vendors', icon: Building2, roles: ['ciso', 'procurement', 'auditor'] },
  { path: '/alerts', label: 'Alerts', icon: Bell, roles: ['ciso', 'procurement', 'auditor'] },
  { path: '/reports', label: 'Reports', icon: FileBarChart, roles: ['ciso', 'procurement'] },

  { path: '/settings', label: 'Settings', icon: Settings, roles: ['ciso', 'procurement', 'auditor'] },
];

export default function DashboardLayout() {
  const { user, logout, hasRole, isLoading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const { data: alertsSummary } = useQuery({
    queryKey: ['alerts', 'summary'],
    queryFn: () => alertsApi.getSummary(),
    refetchInterval: 5000,
  });

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

  const SidebarContent = () => (
    <div className="flex h-full flex-col bg-sg-surface">
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
              onClick={() => {
                navigate(item.path);
                setMobileMenuOpen(false);
              }}
              className={`flex items-center gap-3 rounded-sm px-3 py-2.5 text-sm uppercase tracking-wider font-semibold transition-all duration-200 ${
                isActive
                  ? 'bg-sg-primary text-white'
                  : 'text-sg-text-secondary hover:bg-sg-surface-muted hover:text-sg-text-primary'
              }`}
            >
              <Icon className="h-[18px] w-[18px]" />
              <span>{item.label}</span>
              {item.label === 'Alerts' && (alertsSummary?.total_open || 0) > 0 && (
                <span className={`ml-auto flex h-5 min-w-[20px] items-center justify-center rounded-sm px-1.5 text-[10px] font-bold ${isActive ? 'bg-white text-sg-primary' : 'bg-sg-primary text-white'}`}>
                  {alertsSummary?.total_open}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Copilot button */}
      <div className="px-3 pb-2">
        <button
          onClick={() => {
            setCopilotOpen(true);
            setMobileMenuOpen(false);
          }}
          className="flex w-full items-center gap-2 rounded-sm bg-gradient-to-r from-violet-600 to-indigo-600 px-3 py-2.5 text-sm font-semibold text-white transition-all hover:from-violet-500 hover:to-indigo-500 hover:-translate-y-0.5 hover:shadow-lg"
        >
          <Sparkles className="h-4 w-4" />
          <span>Copilot</span>
          <span className="ml-auto rounded-full bg-white/20 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider">AI</span>
        </button>
      </div>

      {/* User section */}
      <div className="border-t border-sg-border-subtle px-3 py-4 bg-sg-surface mt-auto">
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
          onClick={() => {
            logout();
            setMobileMenuOpen(false);
          }}
          className="mt-3 flex w-full items-center gap-2 rounded-sm px-3 py-2 text-xs font-semibold uppercase tracking-wider text-sg-text-secondary transition-colors hover:bg-sg-surface-muted hover:text-sg-error"
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen w-full bg-sg-surface-muted">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex h-full w-sidebar flex-shrink-0 flex-col border-r border-sg-border-subtle bg-sg-surface">
        <SidebarContent />
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile Top Bar */}
        <div className="flex lg:hidden h-14 flex-shrink-0 items-center justify-between border-b border-sg-border-subtle bg-sg-surface px-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-sg-secondary" />
            <span className="font-display text-sm font-bold tracking-tight text-sg-text-primary uppercase">VendorSentry</span>
          </div>
          <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
            <SheetTrigger asChild>
              <button className="flex h-8 w-8 items-center justify-center rounded-md text-sg-text-secondary hover:bg-sg-surface-muted hover:text-sg-text-primary">
                <Menu className="h-5 w-5" />
              </button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[280px] p-0 border-r border-sg-border-subtle [&>button]:hidden">
              <SheetTitle className="sr-only">Navigation Menu</SheetTitle>
              <SidebarContent />
            </SheetContent>
          </Sheet>
        </div>

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

      {/* Copilot Panel — global overlay */}
      <CopilotPanel isOpen={copilotOpen} onClose={() => setCopilotOpen(false)} />
    </div>
  );
}

