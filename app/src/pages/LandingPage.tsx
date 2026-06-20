import { ShieldCheck, ArrowRight, Building2, Lock, Activity } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-sg-surface-muted font-sans text-sg-text-primary">
      {/* Header */}
      <header className="flex h-20 items-center justify-between border-b border-sg-border-subtle bg-sg-surface px-8">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center bg-sg-secondary">
            <ShieldCheck className="h-6 w-6 text-sg-text-inverse" />
          </div>
          <span className="font-display text-xl font-bold tracking-tight text-sg-text-primary uppercase">
            VendorSentry
          </span>
        </div>
        <nav className="flex items-center gap-6">
          <a href="#features" className="text-sm font-semibold uppercase tracking-wider text-sg-text-secondary transition-colors hover:text-sg-primary">
            Features
          </a>
          <a href="#platform" className="text-sm font-semibold uppercase tracking-wider text-sg-text-secondary transition-colors hover:text-sg-primary">
            Platform
          </a>
          <button
            onClick={() => navigate('/login')}
            className="flex items-center gap-2 rounded bg-sg-primary px-6 py-2.5 text-sm font-semibold text-sg-text-inverse transition-all hover:bg-sg-primary-hover"
          >
            Client Login
            <ArrowRight className="h-4 w-4" />
          </button>
        </nav>
      </header>

      {/* Hero Section */}
      <main>
        <section className="relative flex min-h-[80vh] flex-col justify-center overflow-hidden border-b border-sg-border-subtle bg-sg-surface px-8 py-20">
          <div className="absolute top-0 right-0 h-[600px] w-[600px] -translate-y-1/4 translate-x-1/4 bg-sg-surface-muted opacity-50"></div>
          <div className="absolute bottom-0 left-0 h-4 w-1/3 bg-sg-primary"></div>
          
          <div className="relative z-10 mx-auto max-w-6xl">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="max-w-3xl"
            >
              <div className="mb-6 flex items-center gap-3">
                <div className="h-4 w-4 bg-sg-primary"></div>
                <span className="text-sm font-semibold uppercase tracking-widest text-sg-text-secondary">
                  Institutional Risk Intelligence
                </span>
              </div>
              <h1 className="font-display text-6xl font-bold leading-tight tracking-tight text-sg-text-primary md:text-7xl">
                Securing the <br /> Third-Party Perimeter.
              </h1>
              <p className="mt-8 text-xl leading-relaxed text-sg-text-secondary max-w-2xl">
                VendorSentry is an AI-powered compliance and risk engine designed for global financial institutions. Monitor vendors, automate document extraction, and resolve operational conflicts with uncompromising precision.
              </p>
              <div className="mt-12 flex gap-4">
                <button
                  onClick={() => navigate('/login')}
                  className="rounded bg-sg-primary px-8 py-4 text-base font-bold uppercase tracking-wider text-sg-text-inverse transition-all hover:bg-sg-primary-hover shadow-lift"
                >
                  Access Platform
                </button>
                <button
                  onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
                  className="rounded border border-sg-border px-8 py-4 text-base font-bold uppercase tracking-wider text-sg-text-primary transition-all hover:border-sg-border-focus"
                >
                  Explore Capabilities
                </button>
              </div>
            </motion.div>
          </div>
        </section>

        {/* Modular Features Section */}
        <section id="features" className="bg-sg-surface-muted px-8 py-24">
          <div className="mx-auto max-w-6xl">
            <div className="mb-16">
              <h2 className="font-display text-4xl font-bold text-sg-text-primary">Core Infrastructure</h2>
              <div className="mt-4 h-1 w-24 bg-sg-primary"></div>
            </div>

            <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
              {/* Feature Block 1 */}
              <div className="group border border-sg-border-subtle bg-sg-surface p-8 transition-all hover:border-sg-border-focus hover:shadow-lift">
                <div className="mb-6 flex h-12 w-12 items-center justify-center bg-sg-surface-muted group-hover:bg-sg-primary group-hover:text-sg-text-inverse transition-colors">
                  <Building2 className="h-6 w-6" />
                </div>
                <h3 className="font-display text-xl font-bold text-sg-text-primary">Vendor Intelligence</h3>
                <p className="mt-4 text-sg-text-secondary">
                  Continuous monitoring of global vendor portfolios with automated risk scoring and Tier-based categorization.
                </p>
              </div>

              {/* Feature Block 2 */}
              <div className="group border border-sg-border-subtle bg-sg-surface p-8 transition-all hover:border-sg-border-focus hover:shadow-lift">
                <div className="mb-6 flex h-12 w-12 items-center justify-center bg-sg-surface-muted group-hover:bg-sg-secondary group-hover:text-sg-text-inverse transition-colors">
                  <Activity className="h-6 w-6" />
                </div>
                <h3 className="font-display text-xl font-bold text-sg-text-primary">AI Contract Analysis</h3>
                <p className="mt-4 text-sg-text-secondary">
                  Advanced extraction of SLA terms, compliance certifications, and data access scopes from dense legal documents.
                </p>
              </div>

              {/* Feature Block 3 */}
              <div className="group border border-sg-border-subtle bg-sg-surface p-8 transition-all hover:border-sg-border-focus hover:shadow-lift">
                <div className="mb-6 flex h-12 w-12 items-center justify-center bg-sg-surface-muted group-hover:bg-sg-primary group-hover:text-sg-text-inverse transition-colors">
                  <Lock className="h-6 w-6" />
                </div>
                <h3 className="font-display text-xl font-bold text-sg-text-primary">Conflict Resolution</h3>
                <p className="mt-4 text-sg-text-secondary">
                  Automated discrepancy detection between stated contractual terms and actual operational records.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Call to Action */}
        <section className="bg-sg-secondary px-8 py-24 text-sg-text-inverse">
          <div className="mx-auto max-w-6xl text-center">
            <h2 className="font-display text-4xl font-bold text-sg-text-inverse">Ready to secure your vendor ecosystem?</h2>
            <p className="mx-auto mt-6 max-w-2xl text-lg text-sg-text-secondary">
              Join leading financial institutions leveraging VendorSentry for uncompromising third-party risk management.
            </p>
            <button
              onClick={() => navigate('/login')}
              className="mt-10 rounded bg-sg-primary px-10 py-4 text-lg font-bold uppercase tracking-wider text-sg-text-inverse transition-all hover:bg-sg-surface hover:text-sg-primary"
            >
              Sign In to Dashboard
            </button>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-sg-border-subtle bg-sg-surface px-8 py-12">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 md:flex-row">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-sg-primary" />
            <span className="font-display font-bold uppercase tracking-tight text-sg-text-primary">VendorSentry</span>
          </div>
          <p className="text-sm font-semibold uppercase text-sg-text-secondary">
            &copy; {new Date().getFullYear()} VendorSentry. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
