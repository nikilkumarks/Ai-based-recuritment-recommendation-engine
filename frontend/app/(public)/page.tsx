import Link from "next/link";
import Image from "next/image";
import { HealthStatus } from "@/components/health-status";
import {
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  Cpu,
  Layers,
  GitBranch,
  Search,
  UserCheck,
  FileText,
  Activity,
  Brain,
  TrendingUp,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="space-y-20 pb-16">
      {/* HERO SECTION */}
      <section className="relative pt-12 pb-8 max-w-6xl mx-auto px-4 sm:px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Left Hero Text Column */}
          <div className="lg:col-span-7 space-y-6 text-left">
            <div className="inline-flex items-center gap-2 rounded-full border border-teal-200/80 bg-teal-50/80 px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-teal-800">
              <ShieldCheck className="h-3.5 w-3.5 text-teal-700" />
              <span>Evidence-Based Talent Matching</span>
            </div>

            <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 leading-[1.15]">
              Match talent by evidence, <br className="hidden sm:inline" />
              <span className="text-teal-700">not keyword overlap.</span>
            </h1>

            <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-2xl font-normal">
              SkillMatch analyzes candidate skills, canonical skill relationships, semantic evidence, and job requirements to produce explainable recruitment matches.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-wrap items-center gap-3.5 pt-2">
              <Link
                href="/register"
                className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-teal-700 px-5 text-sm font-semibold text-white shadow-xs transition-all hover:bg-teal-800 hover:shadow-md focus-visible:outline-2 focus-visible:outline-teal-700"
              >
                <span>Get Started</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/login"
                className="inline-flex h-11 items-center justify-center rounded-lg border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-700 shadow-2xs transition-all hover:bg-slate-50 hover:text-slate-900 hover:border-slate-300"
              >
                Sign In
              </Link>
            </div>

            {/* Feature Trust Points */}
            <div className="grid grid-cols-2 gap-3 pt-6 border-t border-slate-200/80 max-w-xl text-xs font-medium text-slate-600">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                <span>Deterministic skill extraction</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                <span>Canonical skill ontology</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                <span>Semantic evidence</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                <span>Explainable matching</span>
              </div>
            </div>
          </div>

          {/* Right Product Preview Mockup Column */}
          <div className="lg:col-span-5" id="product">
            <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xl shadow-slate-200/50 space-y-4">
              
              {/* Card Header */}
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2.5">
                  <Image
                    src="/Logo.jpeg"
                    alt="SkillMatch Logo"
                    width={28}
                    height={28}
                    className="h-7 w-7 rounded-md object-cover border border-slate-200"
                  />
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 leading-tight">SkillMatch Workspace</h3>
                    <p className="text-[10px] text-slate-500">Evaluation Engine Demo</p>
                  </div>
                </div>
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-semibold text-slate-700 border border-slate-200">
                  Model: Baseline
                </span>
              </div>

              {/* Role Title */}
              <div>
                <h4 className="text-sm font-bold text-slate-900">Senior Frontend Engineer</h4>
                <p className="text-xs text-slate-500 font-medium">Cloud Platform Organization</p>
              </div>

              {/* Match Metrics Grid */}
              <div className="space-y-3 bg-slate-50/80 rounded-xl p-3.5 border border-slate-100">
                {/* Current Match */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-slate-700 font-semibold">Current Match</span>
                    <span className="font-bold text-teal-700">84%</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-200 overflow-hidden">
                    <div className="h-full bg-teal-600 rounded-full w-[84%]" />
                  </div>
                </div>

                {/* Coverage & Potential */}
                <div className="grid grid-cols-2 gap-2 pt-1 text-xs">
                  <div className="rounded-lg bg-white p-2 border border-slate-200/70">
                    <span className="text-[10px] text-slate-500 block uppercase font-semibold">Required Coverage</span>
                    <span className="font-bold text-slate-900 text-sm">8 / 9 (88%)</span>
                  </div>
                  <div className="rounded-lg bg-white p-2 border border-slate-200/70">
                    <span className="text-[10px] text-slate-500 block uppercase font-semibold">Gap Closability</span>
                    <span className="font-bold text-teal-700 text-sm">High Potential</span>
                  </div>
                </div>
              </div>

              {/* Evidence Breakdown */}
              <div className="space-y-2 text-xs">
                <span className="font-bold text-slate-900 block text-[11px] uppercase tracking-wider text-slate-500">
                  Skill Evidence
                </span>
                <div className="flex flex-wrap gap-1.5">
                  <span className="rounded-md bg-teal-50 px-2 py-0.5 text-[11px] font-medium text-teal-800 border border-teal-200/60">✓ React</span>
                  <span className="rounded-md bg-teal-50 px-2 py-0.5 text-[11px] font-medium text-teal-800 border border-teal-200/60">✓ TypeScript</span>
                  <span className="rounded-md bg-teal-50 px-2 py-0.5 text-[11px] font-medium text-teal-800 border border-teal-200/60">✓ Next.js</span>
                  <span className="rounded-md bg-teal-50 px-2 py-0.5 text-[11px] font-medium text-teal-800 border border-teal-200/60">✓ PostgreSQL</span>
                </div>

                <div className="pt-1.5 space-y-1 text-[11px]">
                  <div className="flex items-center gap-1.5 text-rose-700 font-medium">
                    <span className="font-semibold text-slate-700">Missing:</span>
                    <span className="rounded-md bg-rose-50 px-1.5 py-0.5 border border-rose-200">Kubernetes</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-600">
                    <span className="font-semibold text-slate-700">Related evidence:</span>
                    <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-slate-700 border border-slate-200 font-mono text-[10px]">
                      Docker → Kubernetes
                    </span>
                  </div>
                </div>
              </div>

              {/* Footer Note */}
              <div className="border-t border-slate-100 pt-2 text-[10px] text-slate-400 text-center font-medium">
                Visual Demonstration Mockup — Explains match score decomposition
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS SECTION */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-4" id="how-it-works">
        <div className="text-center max-w-3xl mx-auto space-y-3 mb-12">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 border border-slate-200">
            <Cpu className="h-3.5 w-3.5 text-teal-700" />
            <span>Architecture Pipeline</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            How SkillMatch works
          </h2>
          <p className="text-sm text-slate-600">
            A 7-step deterministic and semantic recommendation pipeline that replaces black-box scoring with verifiable evidence.
          </p>
        </div>

        {/* 7 Connected Steps Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              step: "01",
              title: "Resume & Job Input",
              desc: "PDF and DOCX document ingestion with NLP text extraction.",
              icon: FileText,
            },
            {
              step: "02",
              title: "Deterministic Extraction",
              desc: "spaCy phrase matching extracts raw skill entities.",
              icon: Brain,
            },
            {
              step: "03",
              title: "Ontology Mapping",
              desc: "Maps raw text to canonical skill names and alias graphs.",
              icon: GitBranch,
            },
            {
              step: "04",
              title: "Semantic Embeddings",
              desc: "MiniLM-L6-v2 384-dimensional dense vector embeddings.",
              icon: Layers,
            },
            {
              step: "05",
              title: "Baseline Match",
              desc: "TF-IDF and cosine similarity formula calculations.",
              icon: TrendingUp,
            },
            {
              step: "06",
              title: "Explainability",
              desc: "Decomposes scores into required vs preferred evidence and gaps.",
              icon: Search,
            },
            {
              step: "07",
              title: "Recruiter Decision",
              desc: "Structured shortlist / reject logging with audit rationale.",
              icon: UserCheck,
            },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.step}
                className="relative rounded-xl border border-slate-200/90 bg-white p-4.5 shadow-2xs hover:shadow-md transition-all hover:border-teal-200 group"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-50 text-teal-700 font-bold group-hover:bg-teal-700 group-hover:text-white transition-colors">
                    <Icon className="h-4 w-4" />
                  </div>
                  <span className="text-[10px] font-mono font-bold uppercase text-teal-700 bg-teal-50 px-2 py-0.5 rounded-full border border-teal-100">
                    Step {item.step}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-slate-900 mb-1">{item.title}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{item.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* CORE DIFFERENTIATORS */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6" id="evidence">
        <div className="text-center max-w-2xl mx-auto space-y-3 mb-10">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Designed for evidence, transparency, and control
          </h2>
          <p className="text-sm text-slate-600">
            Four core architectural principles that ensure reliable recruitment decision support.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="rounded-xl border border-slate-200/90 bg-white p-6 shadow-2xs space-y-2 hover:border-teal-200 transition-colors">
            <div className="h-8 w-8 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center mb-3">
              <GitBranch className="h-4 w-4" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Skill Ontology</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Canonical skills, aliases, parent-child relationships, and related skills provide structured evidence beyond keyword matching.
            </p>
          </div>

          <div className="rounded-xl border border-slate-200/90 bg-white p-6 shadow-2xs space-y-2 hover:border-teal-200 transition-colors">
            <div className="h-8 w-8 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center mb-3">
              <Search className="h-4 w-4" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Explainable Matching</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Every match can be decomposed into understandable evidence such as required skills, preferred skills, semantic similarity, and experience.
            </p>
          </div>

          <div className="rounded-xl border border-slate-200/90 bg-white p-6 shadow-2xs space-y-2 hover:border-teal-200 transition-colors">
            <div className="h-8 w-8 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center mb-3">
              <TrendingUp className="h-4 w-4" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Potential</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Potential represents gap closability using skill relationships and supporting evidence. It is not a hiring probability.
            </p>
          </div>

          <div className="rounded-xl border border-slate-200/90 bg-white p-6 shadow-2xs space-y-2 hover:border-teal-200 transition-colors">
            <div className="h-8 w-8 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center mb-3">
              <UserCheck className="h-4 w-4" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Human Decisions</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Recruiter decisions remain explicit and auditable rather than being hidden behind an opaque AI score.
            </p>
          </div>
        </div>
      </section>

      {/* CURRENT MATCH VS POTENTIAL SECTION */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6" id="for-recruiters">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-sm space-y-8">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Understand both match and potential
            </h2>
            <p className="text-xs sm:text-sm text-slate-600">
              Clear mathematical separation between existing qualification and candidate growth potential.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left Card: Current Match */}
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-teal-800">Current Match</h3>
                <span className="text-[10px] bg-teal-100 text-teal-900 font-semibold px-2 py-0.5 rounded-full">Demonstrated</span>
              </div>
              <p className="text-xs text-slate-600">
                What the candidate currently demonstrates against the job requirements.
              </p>
              <ul className="space-y-2 text-xs text-slate-700 font-medium">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                  <span>Required skills coverage</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                  <span>Preferred skills alignment</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                  <span>Semantic similarity metrics</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                  <span>Verified experience & education</span>
                </li>
              </ul>
            </div>

            {/* Right Card: Potential */}
            <div className="rounded-xl border border-teal-200 bg-teal-50/40 p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-teal-200/80 pb-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-teal-900">Potential</h3>
                <span className="text-[10px] bg-teal-700 text-white font-semibold px-2 py-0.5 rounded-full">Closability</span>
              </div>
              <p className="text-xs text-slate-600">
                How closable the remaining skill gaps are using related skills, projects, experience, certifications, and semantic evidence.
              </p>
              <div className="rounded-lg bg-white p-3 border border-teal-200/80 text-xs text-teal-900 font-semibold">
                ⚠️ Potential is gap closability, not hiring probability.
              </div>
              <ul className="space-y-2 text-xs text-slate-700 font-medium">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                  <span>Ontology graph relationship paths</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                  <span>Supporting project & certification evidence</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* TECHNICAL FOUNDATION & REAL API CONNECTIVITY */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 space-y-6">
        <div className="text-center max-w-xl mx-auto space-y-2">
          <h2 className="text-xl font-bold text-slate-900">Built on transparent recruitment intelligence</h2>
          <p className="text-xs text-slate-500">Core technologies powering candidate evaluation and graph resolution.</p>
        </div>

        {/* Tech Stack Badges */}
        <div className="flex flex-wrap items-center justify-center gap-2.5">
          {["spaCy NLP", "Skill Ontology", "PostgreSQL", "pgvector", "Sentence Transformers", "Next.js", "FastAPI"].map((tech) => (
            <span
              key={tech}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs"
            >
              {tech}
            </span>
          ))}
        </div>

        {/* Real Backend API Health Connectivity */}
        <div className="max-w-md mx-auto rounded-xl border border-slate-200 bg-white p-4 shadow-2xs text-left">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-teal-600" />
              <span>Backend API Status</span>
            </span>
            <span className="text-[10px] text-slate-500 font-mono">/api/v1/health</span>
          </div>
          <HealthStatus />
        </div>
      </section>

      {/* FINAL CTA SECTION */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="rounded-2xl bg-slate-900 text-white p-8 sm:p-12 text-center space-y-6 shadow-xl relative overflow-hidden">
          <div className="max-w-2xl mx-auto space-y-3 relative z-10">
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Make recruitment decisions easier to explain
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              Review candidate evidence, understand skill gaps, and make structured recruitment decisions with SkillMatch.
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3.5 relative z-10">
            <Link
              href="/register"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-teal-600 px-5 text-sm font-semibold text-white shadow-xs hover:bg-teal-500 transition-colors"
            >
              <span>Get Started</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/login"
              className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-700 bg-slate-800 px-5 text-sm font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-colors"
            >
              Sign In
            </Link>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="max-w-6xl mx-auto px-4 sm:px-6 pt-8 border-t border-slate-200/80">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6 pb-6">
          <div className="flex items-center gap-3">
            <Image
              src="/Logo.jpeg"
              alt="SkillMatch Logo"
              width={28}
              height={28}
              className="h-7 w-7 rounded-md object-cover border border-slate-200"
            />
            <div>
              <span className="text-sm font-bold text-slate-900 block leading-none">SkillMatch</span>
              <span className="text-[10px] text-slate-500 font-medium block mt-0.5">
                AI-Based Recruitment Recommendation Engine
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-xs text-slate-600 font-medium">
            <a href="#product" className="hover:text-teal-700 transition-colors">Product</a>
            <a href="#how-it-works" className="hover:text-teal-700 transition-colors">How It Works</a>
            <Link href="/login" className="hover:text-teal-700 transition-colors">Sign In</Link>
            <Link href="/register" className="hover:text-teal-700 transition-colors">Register</Link>
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-slate-100 py-4 text-[11px] text-slate-500">
          <span>SkillMatch © {new Date().getFullYear()} — Enterprise Recruitment Intelligence</span>
          <span className="font-mono font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
            PRJ_385
          </span>
        </div>
      </footer>
    </div>
  );
}
