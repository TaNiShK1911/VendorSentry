import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import {
  User, Bell, Monitor, KeyRound,
} from 'lucide-react';
import { motion } from 'framer-motion';

const tabs = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'display', label: 'Display', icon: Monitor },
  { id: 'api', label: 'API Keys', icon: KeyRound },
];

export default function SettingsPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [notifications, setNotifications] = useState({
    critical: true,
    digest: false,
    browser: true,
  });
  const [apiKeyVisible, setApiKeyVisible] = useState(false);
  const [density, setDensity] = useState<'compact' | 'comfortable'>('comfortable');
  const [darkMode, setDarkMode] = useState(() => {
    return document.documentElement.classList.contains('dark') || localStorage.getItem('theme') === 'dark';
  });

  const handleDarkModeToggle = (enabled: boolean) => {
    setDarkMode(enabled);
    if (enabled) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-semibold tracking-tight text-sg-text-primary">Settings</h1>

      <div className="mt-6 flex gap-6">
        {/* Sidebar tabs */}
        <div className="w-48 flex-shrink-0">
          <nav className="flex flex-col gap-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all ${
                    activeTab === tab.id
                      ? 'bg-sg-surface-dim text-sg-text-primary'
                      : 'text-sg-text-secondary hover:bg-white/[0.04] hover:text-sg-text-primary'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span className="font-medium">{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="rounded-card border border-sg-border-subtle bg-sg-surface p-6 shadow-card"
            >
              <h2 className="text-lg font-semibold text-sg-text-primary">Profile</h2>
              <div className="mt-4 flex items-center gap-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-sg-surface-dim text-xl font-bold text-sg-text-primary">
                  {user?.name?.split(' ').map((n) => n[0]).join('') || 'U'}
                </div>
                <div>
                  <p className="text-lg font-medium text-sg-text-primary">{user?.name}</p>
                  <p className="text-sm text-sg-text-secondary">{user?.email}</p>
                  <span className={`mt-1 inline-block rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${
                    user?.role === 'ciso' ? 'tier-badge-critical'
                    : user?.role === 'procurement' ? 'tier-badge-high'
                    : 'tier-badge-medium'
                  }`}>
                    {user?.role}
                  </span>
                </div>
              </div>
            </motion.div>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="rounded-card border border-sg-border-subtle bg-sg-surface p-6 shadow-card"
            >
              <h2 className="text-lg font-semibold text-sg-text-primary">Notification Preferences</h2>
              <div className="mt-4 space-y-4">
                {[
                  { key: 'critical', label: 'Critical Event Emails', desc: 'Receive email alerts for critical vendor risk events' },
                  { key: 'digest', label: 'Daily Digest', desc: 'Receive a daily summary of all vendor activity' },
                  { key: 'browser', label: 'Browser Notifications', desc: 'Show real-time notifications in your browser' },
                ].map((item) => (
                  <div key={item.key} className="flex items-center justify-between border-b border-sg-border-subtle pb-4 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-sg-text-primary">{item.label}</p>
                      <p className="text-xs text-sg-text-secondary">{item.desc}</p>
                    </div>
                    <label className="relative inline-flex cursor-pointer items-center">
                      <input
                        type="checkbox"
                        checked={notifications[item.key as keyof typeof notifications]}
                        onChange={(e) => setNotifications((prev) => ({ ...prev, [item.key]: e.target.checked }))}
                        className="peer sr-only"
                      />
                      <div className="h-6 w-11 rounded-full bg-sg-surface-muted border border-sg-border-subtle after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all peer-checked:bg-sg-primary peer-checked:after:translate-x-full" />
                    </label>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Display Tab */}
          {activeTab === 'display' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4"
            >
              <div className="rounded-card border border-sg-border-subtle bg-sg-surface p-6 shadow-card">
                <h2 className="text-lg font-semibold text-sg-text-primary">Theme</h2>
                <div className="mt-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-sg-text-primary">Dark Mode</p>
                    <p className="text-xs text-sg-text-secondary">Switch to a premium dark-themed interface</p>
                  </div>
                  <label className="relative inline-flex cursor-pointer items-center">
                    <input
                      type="checkbox"
                      checked={darkMode}
                      onChange={(e) => handleDarkModeToggle(e.target.checked)}
                      className="peer sr-only"
                    />
                    <div className="h-6 w-11 rounded-full bg-sg-surface-muted border border-sg-border-subtle after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all peer-checked:bg-sg-primary peer-checked:after:translate-x-full" />
                  </label>
                </div>
              </div>

              <div className="rounded-card border border-sg-border-subtle bg-sg-surface p-6 shadow-card">
                <h2 className="text-lg font-semibold text-sg-text-primary">Density</h2>
                <div className="mt-4 flex gap-3">
                  {(['compact', 'comfortable'] as const).map((d) => (
                    <button
                      key={d}
                      onClick={() => setDensity(d)}
                      className={`rounded-lg border px-6 py-3 text-sm font-medium capitalize transition-all ${
                        density === d
                          ? 'border-vs-accent-blue bg-sg-surface-dim text-sg-text-primary'
                          : 'border-sg-border-subtle bg-sg-surface-muted border border-sg-border-subtle text-sg-text-secondary hover:text-sg-text-primary'
                      }`}
                    >
                      {d}
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {/* API Keys Tab */}
          {activeTab === 'api' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="rounded-card border border-sg-border-subtle bg-sg-surface p-6 shadow-card"
            >
              <h2 className="text-lg font-semibold text-sg-text-primary">API Keys</h2>
              <div className="mt-4">
                <label className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-sg-text-secondary">
                  API Key
                </label>
                <div className="flex gap-2">
                  <div className="flex-1 rounded-input border border-sg-border-subtle bg-sg-surface-muted border border-sg-border-subtle px-4 py-3 font-mono text-sm text-sg-text-secondary">
                    {apiKeyVisible ? 'vs_live_51H8m...xK9pQ2' : '••••••••••••••••••••••'}
                  </div>
                  <button
                    onClick={() => setApiKeyVisible(!apiKeyVisible)}
                    className="rounded-button border border-sg-border-subtle bg-sg-surface-muted border border-sg-border-subtle px-4 py-2.5 text-sm text-sg-text-secondary hover:text-sg-text-primary"
                  >
                    {apiKeyVisible ? 'Hide' : 'Show'}
                  </button>
                </div>
                <button className="mt-3 text-sm text-sg-text-primary hover:underline">
                  Regenerate Key
                </button>
              </div>

              <div className="mt-6 grid grid-cols-2 gap-4">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Requests Today</p>
                  <p className="mt-1 text-lg font-semibold text-sg-text-primary">1,247</p>
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-sg-text-secondary">Rate Limit</p>
                  <p className="mt-1 text-lg font-semibold text-sg-text-primary">10,000/hr</p>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
