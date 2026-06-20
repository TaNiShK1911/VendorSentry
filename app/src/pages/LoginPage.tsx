import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Loader2, Shield, ShieldCheck, ShieldOff } from 'lucide-react';

const ROLES = [
  { id: 'ciso', label: 'CISO', icon: Shield },
  { id: 'procurement', label: 'Procurement', icon: ShieldCheck },
  { id: 'auditor', label: 'Auditor', icon: ShieldOff },
] as const;

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, loginLoading, loginError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [selectedRole, setSelectedRole] = useState<string>('ciso');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login({ email, password });
      navigate('/dashboard');
    } catch {
      // Error is handled by loginError
    }
  };

  const handleRoleSelect = (roleId: string) => {
    setSelectedRole(roleId);
    if (roleId === 'ciso') setEmail('ciso@company.com');
    else if (roleId === 'procurement') setEmail('procurement@company.com');
    else if (roleId === 'auditor') setEmail('auditor@company.com');
    setPassword('password123');
  };

  return (
    <div className="flex min-h-screen flex-col bg-white font-sans text-sg-text-primary">
      {/* Header */}
      <header className="flex h-20 items-center justify-between border-b border-sg-border-subtle bg-white px-8">
        <Link to="/" className="flex items-center gap-3 hover:opacity-90">
          <div className="flex h-10 w-10 items-center justify-center bg-sg-secondary">
            <ShieldCheck className="h-6 w-6 text-white" />
          </div>
          <span className="font-display text-xl font-bold uppercase tracking-tight text-sg-text-primary">
            VendorSentry
          </span>
        </Link>
      </header>

      {/* Main Content */}
      <main className="flex flex-1">
        {/* Left column - Discovery (SG inspired, but VendorSentry features) */}
        <div className="hidden w-1/3 flex-col bg-[#F2F2F2] lg:flex">
          <div className="mt-32 px-12">
            <div className="mb-8 h-1 w-8 bg-black"></div>
            <h1 className="max-w-xs font-display text-4xl font-bold leading-tight text-black">
              Discover more on VendorSentry
            </h1>
            
            <p className="mt-6 max-w-sm text-sm leading-relaxed text-[#5A5A5A]">
              AI-powered third-party risk monitoring, document intelligence, and compliance scoring — all in one platform.
            </p>
          </div>
        </div>

        {/* Right column - Login panel */}
        <div className="flex flex-1 items-start justify-center pt-20 lg:pt-24">
          <div className="w-full max-w-[440px] px-6">
            <h2 className="mb-8 font-display text-3xl font-bold tracking-tight text-black">
              Sign in to VendorSentry
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email */}
              <div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email"
                  className="w-full bg-[#EAEAEA] px-4 py-3.5 text-sm text-black placeholder-[#808080] outline-none transition-all focus:ring-2 focus:ring-black/5"
                  required
                />
              </div>

              {/* Password */}
              <div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  className="w-full bg-[#EAEAEA] px-4 py-3.5 text-sm text-black placeholder-[#808080] outline-none transition-all focus:ring-2 focus:ring-black/5"
                  required
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                {/* Extras removed */}
              </div>

              {/* Role selector (Original Functionality Restored in SG Style) */}
              <div className="pt-6">
                <label className="text-[11px] font-semibold uppercase tracking-wider text-[#5A5A5A]">
                  Demo Login Roles
                </label>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  {ROLES.map((role) => {
                    const RoleIcon = role.icon;
                    const isSelected = selectedRole === role.id;
                    return (
                      <button
                        key={role.id}
                        type="button"
                        onClick={() => handleRoleSelect(role.id)}
                        className={`flex flex-col items-center gap-2 border p-4 transition-all ${
                          isSelected
                            ? 'border-sg-primary bg-[#F9F9F9] text-black'
                            : 'border-[#EAEAEA] bg-white text-[#808080] hover:border-[#A0A0A0]'
                        }`}
                      >
                        <RoleIcon className={`h-5 w-5 ${isSelected ? 'text-sg-primary' : ''}`} />
                        <span className="text-xs font-bold uppercase tracking-wider">{role.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Error */}
              {loginError && (
                <div className="mt-2 rounded bg-sg-risk-red-bg px-4 py-3 text-sm text-sg-risk-red">
                  {loginError instanceof Error ? loginError.message : 'Login failed. Please try again.'}
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={loginLoading}
                className="mt-8 flex w-full items-center justify-center bg-[#949494] py-3.5 text-sm font-semibold text-white transition-all hover:bg-[#808080] disabled:opacity-50"
              >
                {loginLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Sign in'}
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
