import Link from "next/link";
import "./landing.css";

/* Empat agent AI DEXTRA (C:\dextra). Disalin inline dari struktur WORKERS
   D:\dextra — hanya field yang dipakai halaman ini: slug, name, role, type,
   purpose, capabilities. Deskripsi mengikuti domain C: Finance, HR,
   Inventory, Operations. */
const WORKERS = [
  {
    slug: "finance-agent",
    name: "Finance Agent",
    role: "Keuangan",
    type: "finance",
    purpose: "Mengestimasi payroll dan menyusun laporan keuangan berbasis data ledger dan transaksi.",
    capabilities: ["payroll_estimation", "financial_reporting", "ledger_analysis"]
  },
  {
    slug: "hr-agent",
    name: "HR Agent",
    role: "Sumber Daya Manusia",
    type: "hr",
    purpose: "Mengelola data karyawan, departemen, absensi, cuti, dan payroll beserta laporannya.",
    capabilities: ["employee_management", "attendance_tracking", "leave_management", "payroll"]
  },
  {
    slug: "inventory-agent",
    name: "Inventory Agent",
    role: "Persediaan",
    type: "inventory",
    purpose: "Memantau stok dan persediaan, serta menyiapkan pengadaan (procurement) sesuai kebutuhan.",
    capabilities: ["stock_monitoring", "inventory_management", "procurement"]
  },
  {
    slug: "operations-agent",
    name: "Operations Agent",
    role: "Operasional",
    type: "operations",
    purpose: "Mengelola proses operasional, tugas, dan koordinasi antar-domain seperti HR, Finance, dan Inventory.",
    capabilities: ["process_management", "task_management", "cross_domain_coordination"]
  }
];

const t = (s: string) => s;

export const metadata = {
  title: "DEXTRA — Governed Enterprise AI Workforce & Operations Platform",
  description:
    "Specialized AI workers. Human-defined authority. Accountable execution. DEXTRA mengelola AI worker, work package, mandat, persetujuan manusia, dan jejak audit dalam satu platform."
};

/* Ikon diambil dari referensi desain (gaya heroicons outline) supaya bentuknya
   sama persis. Ditulis inline, bukan pustaka ikon, karena halaman publik tidak
   boleh menambah dependensi runtime. */
const icon = {
  layers: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
    </svg>
  ),
  arrowRight: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 5l7 7m0 0l-7 7m7-7H3" />
    </svg>
  ),
  chevron: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 5l7 7-7 7" />
    </svg>
  ),
  arrowLong: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 8l4 4m0 0l-4 4m4-4H3" />
    </svg>
  ),
  playCircle: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
      <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  checkCircleSolid: (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" clipRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" />
    </svg>
  ),
  lock: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
    </svg>
  ),
  shieldCheck: (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
  stack: (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
  ),
  clipboardList: (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
    </svg>
  ),
  fingerprint: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 004 11a7.978 7.978 0 002.008 5.253" />
    </svg>
  ),
  checkCircle: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  code: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
    </svg>
  ),
  kanban: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
    </svg>
  ),
  key: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
    </svg>
  ),
  chat: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
    </svg>
  ),
  document: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  monitor: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  ),
  chatBubble: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  ),
  puzzle: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" />
    </svg>
  ),
  bolt: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
  telegram: (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
    </svg>
  )
};

/* Tiga pilar. Isi disalin dari narasi tata kelola produk, bukan dari referensi
   desain — teksnya sama, hanya angka karangan yang dibuang. */
const PILLARS = [
  {
    tone: "indigo" as const,
    focus: false,
    glyph: icon.stack,
    title: "Specialized Intelligence",
    body: "Bukan bot serba bisa. DEXTRA membagi beban kerja ke empat spesialis dengan batasan kemampuan dan konteks yang berbeda-beda.",
    bullets: ["Peran fungsional terisolasi dan terukur", "Sintesis berbasis bukti, bukan asumsi"]
  },
  {
    tone: "purple" as const,
    focus: true,
    glyph: icon.shieldCheck,
    title: "Human-Defined Authority",
    body: "Batas wewenang yang tidak bisa dilanggar. Membaca boleh otonom; mengubah status, memodifikasi data, atau mengirim keluar wajib otorisasi manusia.",
    bullets: ["Persetujuan manusia sebelum eksekusi", "Mandat bertanda tangan untuk tiap tindakan"]
  },
  {
    tone: "fuchsia" as const,
    focus: false,
    glyph: icon.clipboardList,
    title: "Accountable Execution",
    body: "Setiap rencana menghasilkan jejak audit permanen: siapa menyusun, apa yang diperiksa, dan siapa yang menyetujui.",
    bullets: ["Jejak audit untuk setiap tindakan", "Perbandingan rencana sebelum dijalankan"]
  }
];

const STEPS = [
  { n: 1, key: "Request", body: "Anda mengajukan tugas operasional lewat AI Workspace." },
  { n: 2, key: "Understand", body: "Sistem memahami maksud permintaan dan memilih spesialis yang sesuai." },
  { n: 3, key: "Plan", body: "Spesialis menyusun rincian rencana dan tindakan yang akan dijalankan." },
  { n: 4, key: "Validate", body: "Risiko ditandai, dan validator kebijakan memeriksa batas mandat." },
  { n: 5, key: "Approve", body: "Anda memeriksa rencana dan tindakannya, lalu memutuskan setuju atau tolak. Langkah ini tidak bisa dilewati." },
  { n: 6, key: "Execute", body: "Mandat terbit dari persetujuan Anda, dan eksekusi tercatat di jejak audit." }
];

/* Enam instrumen kendali. Tiap kartu hanya memuat ikon, nama fitur, dan satu
   penjelasan fungsi — tidak ada sublabel atau panel detail yang mengulang isi
   kalimat di atasnya. */
const FEATURES = [
  {
    tone: "purple" as const,
    glyph: icon.checkCircle,
    title: "Interlock Approval Center",
    body: "Antrean persetujuan berjenjang: rencana dan tindakannya ditampilkan berdampingan sebelum Anda menandatangani."
  },
  {
    tone: "indigo" as const,
    glyph: icon.code,
    title: "Configuration Delta Inspector",
    body: "Perbandingan konfigurasi antara dasar yang berlaku dan usulan perubahan, sebelum perubahan itu diterapkan."
  },
  {
    tone: "emerald" as const,
    glyph: icon.kanban,
    title: "Execution Task Board",
    body: "Papan tugas dengan tahap yang jelas, sehingga posisi setiap pekerjaan terlihat tanpa perlu bertanya."
  },
  {
    tone: "amber" as const,
    glyph: icon.key,
    title: "Mandate & Boundary Limits",
    body: "Mandat menetapkan apa yang boleh dilakukan, untuk berapa lama, dan atas dasar persetujuan siapa."
  },
  {
    tone: "fuchsia" as const,
    glyph: icon.chat,
    title: "AI Assistant Console",
    body: "Percakapan dengan empat spesialis sesuai perannya, dan setiap jawaban berhenti di persetujuan Anda."
  },
  {
    tone: "blue" as const,
    glyph: icon.document,
    title: "Cryptographic Audit Center",
    body: "Catatan eksekusi permanen dengan hash per rencana, sehingga isi yang disetujui tidak bisa diubah diam-diam."
  }
];

const INTEGRATIONS = [
  {
    tone: "purple" as const,
    glyph: icon.monitor,
    title: "Web Dashboard",
    live: true,
    body: "Aplikasi Next.js 16 dan React 19 dengan mode terang dan gelap, navigasi berjenjang, serta manajemen paket kerja."
  },
  {
    tone: "indigo" as const,
    glyph: icon.chatBubble,
    title: "AI Assistant Console",
    live: true,
    body: "Konsol bahasa alami untuk meminta draf, memecah tugas, dan menilai risiko sebelum diajukan."
  },
  {
    tone: "blue" as const,
    glyph: icon.puzzle,
    title: "MCP Server",
    live: true,
    body: "Gateway Model Context Protocol untuk menghubungkan alat dan sumber data dengan batas izin yang jelas."
  },
  {
    tone: "fuchsia" as const,
    glyph: icon.bolt,
    title: "AI Provider (OpenAI-compatible)",
    live: true,
    body: "Model dipilih lewat konfigurasi server, bukan di browser. Bisa OpenAI, DeepSeek, Qwen, atau endpoint sendiri."
  },
  {
    tone: "muted" as const,
    glyph: icon.chatBubble,
    title: "WhatsApp Approval",
    live: false,
    body: "Notifikasi dan otorisasi lewat WhatsApp Business API. Belum dirilis; jangan diandalkan untuk demo."
  },
  {
    tone: "muted" as const,
    glyph: icon.telegram,
    title: "Telegram Ops Stream",
    live: false,
    body: "Umpan telemetri untuk pengawas saat rencana tertahan atau mandat dibekukan. Masih tahap pengembangan."
  }
];

const VALUES = [
  { n: "01", title: "Reduced Manual Coordination", body: "Tidak perlu bolak-balik menanyakan status. Koordinasi antar-spesialis tercatat di satu alur." },
  { n: "02", title: "Clear Operational Visibility", body: "Posisi setiap pekerjaan terlihat: sedang disusun, sedang ditinjau, atau menunggu persetujuan Anda." },
  { n: "03", title: "Controlled AI Execution", body: "Aksi keluar tidak bergantung pada tebakan model. Validator memeriksa batas, manusia memegang keputusan." },
  { n: "04", title: "Traceable Decisions", body: "Setiap persetujuan mencatat siapa yang memberi wewenang dan atas dasar rencana yang mana." },
  { n: "05", title: "Centralized Governance", body: "Satu tempat untuk mengatur mandat, peran, dan batas tindakan di seluruh workforce." }
];

const NAV = [
  { href: "#hero", label: "Beranda" },
  { href: "#governance", label: "Tentang" },
  { href: "#workforce", label: "AI Workforce" },
  { href: "#workflow", label: "Cara Kerja" },
  { href: "#features", label: "Kontrol & Audit" },
  { href: "#integrations", label: "Integrasi" }
];

const FOOTER_COLS = [
  {
    title: "Product",
    links: [
      { href: "/overview", label: "Operations Overview" },
      { href: "/approvals", label: "Approval Inbox" },
      { href: "/tasks", label: "Task Board" },
      { href: "/reports", label: "Work Packages" },
      { href: "/audit-logs", label: "Audit Ledger" }
    ]
  },
  {
    title: "Workforce",
    links: [
      { href: "/ai-workspace", label: "AI Workspace" },
      { href: "/agents", label: "AI Assistant" },
      { href: "/agents", label: "Workforce" },
      { href: "/governance", label: "Mandat" }
    ]
  },
  {
    title: "Platform & Docs",
    links: [
      { href: "/integrations", label: "Integrasi" },
      { href: "/login", label: "Masuk" }
    ]
  }
];

export default function LandingPage() {
  return (
    <div className="lp">
      {/* ======================= A. HEADER ======================= */}
      <header className="lp-header">
        <div className="lp-header__inner">
          <Link className="lp-brand" href="/" aria-label={t("DEXTRA — beranda")}>
            <span className="lp-brand__mark">
              <span>{icon.layers}</span>
            </span>
            <span className="lp-brand__text">
              <span className="lp-brand__row">
                <span className="lp-brand__name">DEXTRA</span>
                <span className="lp-brand__tag">Governed AI</span>
              </span>
              <span className="lp-brand__sub">AI WORKFORCE OS</span>
            </span>
          </Link>

          <nav className="lp-nav" aria-label="Navigasi utama">
            {NAV.map((item) => (
              <a key={item.href} href={item.href}>{t(item.label)}</a>
            ))}
          </nav>

          <div className="lp-header__actions">
            <Link className="lp-signin" href="/login">{t("Masuk")}</Link>
            <Link className="lp-btn lp-btn--grad" href="/overview">
              <span>{t("Buka Dashboard")}</span>
              <span className="lp-btn__arrow">{icon.arrowRight}</span>
            </Link>
          </div>
        </div>
      </header>

      {/* ======================= B. HERO ======================= */}
      <section className="lp-hero" id="hero">
        <span className="lp-hero__glow-a" aria-hidden="true" />
        <span className="lp-hero__glow-b" aria-hidden="true" />

        <div className="lp-wrap lp-hero__inner">
          <div className="lp-pill-wrap">
            <div className="lp-pill">
              <span className="lp-dot" aria-hidden="true" />
              <span className="lp-pill__label">{t("Prinsip Inti:")}</span>
              <span>&ldquo;{t("Baca boleh otomatis, tulis harus lewat mandat.")}&rdquo;</span>
              {icon.chevron}
            </div>
          </div>

          <div className="lp-hero__head">
            <h1 className="lp-hero__title">
              {t("Transform the Way Your Organization")} <br />
              <span className="lp-gradient-text">{t("Works with Governed AI.")}</span>
            </h1>
            <p className="lp-hero__lead">
              {t("Temui")} <strong>DEXTRA</strong>,{" "}
              {t(
                "platform AI workforce terotorisasi yang mengoordinasikan empat spesialis independen, merapikan operasional kantor, dan menjaga setiap aksi kritis tetap di bawah mandat otoritas manusia."
              )}
            </p>

            <div className="lp-hero__cta">
              <Link className="lp-btn lp-btn--dark" href="/login">
                <span>{t("Explore DEXTRA")}</span>
                <span className="lp-btn__arrow">{icon.arrowLong}</span>
              </Link>
              <a className="lp-btn lp-btn--ghost" href="#workflow">
                <span style={{ color: "var(--lp-purple-600)", display: "inline-flex" }}>{icon.playCircle}</span>
                <span>{t("Pelajari Alur Mandat")}</span>
              </a>
            </div>

            <div className="lp-trust">
              <div className="lp-trust__item">{icon.checkCircleSolid}<span>{t("4 Spesialis AI")}</span></div>
              <div className="lp-trust__item">{icon.checkCircleSolid}<span>{t("Validator kebijakan deterministik (non-LLM)")}</span></div>
              <div className="lp-trust__item">{icon.checkCircleSolid}<span>{t("Jejak audit permanen")}</span></div>
            </div>
          </div>

          {/* Mockup antarmuka. Digambar dengan elemen, bukan tangkapan layar,
              supaya tidak bergantung pada berkas gambar dari luar. */}
          <div className="lp-mock">
            <span className="lp-mock__glow" aria-hidden="true" />
            <div className="lp-mock__frame">
              <div className="lp-mock__bar">
                <div style={{ display: "flex", alignItems: "center" }}>
                  <span className="lp-mock__dots" aria-hidden="true">
                    <span /><span /><span />
                  </span>
                  <span className="lp-mock__url">
                    {icon.lock}
                    <span>dextra / overview</span>
                  </span>
                </div>
                <div className="lp-mock__meta">
                  <span className="lp-mock__chip">
                    <span aria-hidden="true" />
                    {t("Validator: deterministik")}
                  </span>
                  <span>{t("Mode demo")}</span>
                </div>
              </div>

              <div className="lp-mock__body">
                <div className="lp-mock__side" aria-hidden="true">
                  <span className="lp-mock__nav lp-mock__nav--on">{t("Overview")}</span>
                  <span className="lp-mock__nav">{t("Rencana")}</span>
                  <span className="lp-mock__nav">{t("Mandat")}</span>
                  <span className="lp-mock__nav">{t("Audit")}</span>
                  <span className="lp-mock__nav">{t("Spesialis")}</span>
                </div>
                <div className="lp-mock__main">
                  <div className="lp-mock__head">
                    <div>
                      <h3>{t("Overview")}</h3>
                      <small>{t("Ringkasan operasional hari ini")}</small>
                    </div>
                    <span className="lp-mock__status">{t("Sesi aktif")}</span>
                  </div>

                  <div className="lp-mock__kpis">
                    <div className="lp-mock__kpi"><b>4</b><i>{t("Spesialis")}</i></div>
                    <div className="lp-mock__kpi"><b>3</b><i>{t("Menunggu persetujuan")}</i></div>
                    <div className="lp-mock__kpi"><b>12</b><i>{t("Tindakan bermandat")}</i></div>
                  </div>

                  <div className="lp-mock__rows">
                    <div className="lp-mock__row">
                      <span>{t("Rapat koordinasi · 13 Nov 10.00")}</span>
                      <span className="lp-mock__state lp-mock__state--wait">{t("Menunggu Anda")}</span>
                    </div>
                    <div className="lp-mock__row">
                      <span>{t("Notulen rapat operasional")}</span>
                      <span className="lp-mock__state lp-mock__state--done">{t("Mandat terbit")}</span>
                    </div>
                    <div className="lp-mock__row">
                      <span>{t("Follow-up Keuangan · 13 Nov 13.15")}</span>
                      <span className="lp-mock__state lp-mock__state--wait">{t("Menunggu Anda")}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="lp-mock__badge lp-mock__badge--bl">
              <span className="lp-mock__badge-icon">{icon.shieldCheck}</span>
              <div>
                <div className="lp-mock__badge-title">
                  <span>{t("Rencana ditahan")}</span>
                  <em>Interlock</em>
                </div>
                <p>{t("Eksekusi berhenti sampai Anda menandatangani. Tidak ada jalur pintas.")}</p>
              </div>
            </div>

            <div className="lp-mock__badge lp-mock__badge--tr">
              <span className="lp-mock__quorum">
                <span aria-hidden="true" />
                {t("Setiap tindakan berhenti di persetujuan manusia")}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ==================== C. TATA KELOLA ==================== */}
      <section className="lp-section lp-section--white" id="governance">
        <div className="lp-wrap">
          <div className="lp-sec-head">
            <span className="lp-kicker">{t("Governance Architecture")}</span>
            <h2>{t("AI Workforce. Human Authority. Complete Accountability.")}</h2>
            <p>
              {t(
                "DEXTRA menutup risiko eksekusi liar dari model yang tidak deterministik. Setiap inisiatif operasional dibatasi tiga fondasi yang sama di semua halaman."
              )}
            </p>
          </div>

          <div className="lp-grid-3">
            {PILLARS.map((pillar, index) => (
              <div key={pillar.title} className={`lp-pillar${pillar.focus ? " lp-pillar--focus" : ""}`}>
                <div className={`lp-icon-tile lp-icon-tile--${pillar.tone}`}>{pillar.glyph}</div>
                <span className={`lp-pillar__kicker lp-pillar__kicker--${pillar.tone}`}>
                  Pillar 0{index + 1}
                </span>
                <h3>{t(pillar.title)}</h3>
                <p>{t(pillar.body)}</p>
                <ul className={`lp-bullets lp-bullets--${pillar.tone}`}>
                  {pillar.bullets.map((bullet) => <li key={bullet}>{t(bullet)}</li>)}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ==================== D. EMPAT SPESIALIS ==================== */}
      <section className="lp-section lp-section--tint" id="workforce">
        <div className="lp-wrap">
          <div className="lp-sec-head">
            <span className="lp-kicker lp-kicker--solid">{t("The 4 AI Specialists")}</span>
            <h2>{t("Meet the Specialized Workers Behind Your Operations.")}</h2>
            <p>
              {t(
                "DEXTRA dirancang dengan tepat empat spesialis. Tidak ada bot generik: setiap agen punya peran fungsional dan kapabilitas yang saling memeriksa."
              )}
            </p>
          </div>

          <div className="lp-grid-4">
            {WORKERS.map((worker, index) => {
              const tone = ["blue", "purple", "amber", "rose"][index] ?? "purple";
              return (
                <div className="lp-worker" key={worker.slug}>
                  <div>
                    <div className="lp-worker__top">
                      <span className={`lp-worker__num lp-worker__num--${tone}`}>
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <span className="lp-chip lp-chip--role">{worker.role}</span>
                    </div>
                    <h3>{worker.name}</h3>
                    <p className="lp-worker__node">{worker.type} · {worker.role}</p>
                    <p className="lp-worker__desc">{t(worker.purpose)}</p>
                  </div>
                  <div className="lp-worker__foot">
                    <span>{t("Kapabilitas")}</span>
                    <span className="lp-worker__caps">
                      {worker.capabilities.map((capability) => (
                        <code key={capability}>{capability}</code>
                      ))}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="lp-policy">
            <div className="lp-policy__left">
              <span className="lp-policy__icon">{icon.fingerprint}</span>
              <div>
                <div className="lp-policy__title">
                  <span>{t("Arsitektur Kunci: Policy Validator BUKAN AI Worker")}</span>
                  <em>{t("Deterministic Engine")}</em>
                </div>
                <p>
                  {t("Policy Validator adalah mesin aturan yang")} <strong>{t("tidak memakai LLM")}</strong>.{" "}
                  {t(
                    "Ia memeriksa izin, kebijakan, dan kelayakan tindakan sebelum instruksi mencapai sistem produksi — sehingga hasilnya bisa diulang dan tidak bergantung pada tebakan model."
                  )}
                </p>
              </div>
            </div>
            <span className="lp-policy__code">{t("non-LLM · hasil dapat diulang")}</span>
          </div>
        </div>
      </section>

      {/* ==================== E. ALUR KERJA ==================== */}
      <section className="lp-section lp-section--white" id="workflow">
        <div className="lp-wrap">
          <div className="lp-sec-head">
            <span className="lp-kicker">{t("Operational Flow")}</span>
            <h2>{t("From Human Request to Governed Execution.")}</h2>
            <p>
              {t(
                "Setiap tahap terlihat. Tidak ada kotak hitam, dan tidak ada eksekusi tanpa verifikasi izin serta tinjauan manusia."
              )}
            </p>
          </div>

          <div className="lp-grid-6">
            {STEPS.map((step) => {
              const key = step.n === 5;
              return (
                <div key={step.key} className={`lp-step${key ? " lp-step--key" : ""}`}>
                  <div className={`lp-step__num lp-step__num--${step.n}`}>{step.n}</div>
                  <span className={`lp-step__kicker lp-step__kicker--${step.n}`}>
                    {t("Langkah")} {step.n}{key ? ` (${t("Kunci")})` : ""}
                  </span>
                  <h4>{t(step.key)}</h4>
                  <p>{t(step.body)}</p>
                </div>
              );
            })}
          </div>

          <div className="lp-callout">
            <div className="lp-callout__left">
              <span className="lp-callout__mark" aria-hidden="true">§</span>
              <div>
                <h4>{t("Fondasi Utama Filosofi Keamanan DEXTRA")}</h4>
                <p>&ldquo;{t("Read operations can be automated. Write operations require human-defined authority.")}&rdquo;</p>
              </div>
            </div>
            <Link className="lp-callout__link" href="/overview">{t("Lihat Dashboard")} →</Link>
          </div>
        </div>
      </section>

      {/* ==================== F. PUSAT KENDALI ==================== */}
      <section className="lp-section lp-section--tint" id="features">
        <div className="lp-wrap">
          <div className="lp-sec-head">
            <span className="lp-kicker lp-kicker--solid">{t("Enterprise Control Center")}</span>
            <h2>{t("Everything Under Your Control.")}</h2>
            <p>
              {t(
                "Enam instrumen kendali utama untuk kepatuhan, mitigasi risiko, dan audit — semuanya ada di dalam aplikasi yang sama."
              )}
            </p>
          </div>

          <div className="lp-grid-3">
            {FEATURES.map((feature) => (
              <div className="lp-feature" key={feature.title}>
                <div className={`lp-feature__icon lp-feature__icon--${feature.tone}`}>{feature.glyph}</div>
                <h3>{t(feature.title)}</h3>
                <p>{t(feature.body)}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ==================== G. INTEGRASI ==================== */}
      <section className="lp-section lp-section--white" id="integrations">
        <div className="lp-wrap">
          <div className="lp-sec-head">
            <span className="lp-kicker">{t("Ecosystem Connectivity")}</span>
            <h2>{t("One Workforce. Multiple Ways to Collaborate.")}</h2>
            <p>
              {t(
                "DEXTRA menjadi pusat orkestrasi antara operator manusia, dashboard operasional, AI worker, dan antarmuka eksternal."
              )}
            </p>
          </div>

          <div className="lp-grid-3 lp-grid-3--tight">
            {INTEGRATIONS.map((item) => (
              <div className={`lp-integration${item.live ? "" : " lp-integration--soon"}`} key={item.title}>
                <span className={`lp-integration__icon lp-integration__icon--${item.tone}`}>{item.glyph}</span>
                <div>
                  <div className="lp-integration__title">
                    <h4>{item.title}</h4>
                    <span className={`lp-tag ${item.live ? "lp-tag--live" : "lp-tag--soon"}`}>
                      {item.live ? t("Tersedia") : t("Roadmap")}
                    </span>
                  </div>
                  <p>{t(item.body)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ==================== H. DAMPAK ==================== */}
      <section className="lp-section lp-section--tint">
        <div className="lp-wrap">
          <div className="lp-sec-head">
            <span className="lp-kicker lp-kicker--solid">{t("Measurable Value")}</span>
            <h2>{t("Make Your Operations More Organized, Visible, and Accountable.")}</h2>
            <p>
              {t(
                "Tanpa klaim angka yang tidak bisa dibuktikan. Yang berubah adalah cara kerja: koordinasi tercatat, posisi pekerjaan terlihat, dan keputusan punya jejak."
              )}
            </p>
          </div>

          <div className="lp-grid-3">
            {VALUES.map((value) => (
              <div className="lp-value" key={value.n}>
                <div className="lp-value__num">{value.n}</div>
                <h3>{t(value.title)}</h3>
                <p>{t(value.body)}</p>
              </div>
            ))}

            {/* Kartu ini menggantikan angka SLA karangan di referensi desain. */}
            <div className="lp-value lp-value--cta">
              <div>
                <span className="lp-value__eyebrow">{t("Coba sendiri")}</span>
                <h3>{t("Lihat alurnya dari ujung ke ujung")}</h3>
                <p>{t("Buka AI Workspace, pilih satu agent, dan ikuti rencananya sampai persetujuan.")}</p>
              </div>
              <Link className="lp-value__link" href="/ai-workspace">
                {t("Buka AI Workspace")} <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ==================== I. CTA AKHIR ==================== */}
      <section className="lp-final">
        <span className="lp-final__bg" aria-hidden="true" />
        <span className="lp-final__glow" aria-hidden="true" />
        <div className="lp-final__inner">
          <span className="lp-final__pill">
            <span aria-hidden="true" />
            {t("Ready to Transform Operations")}
          </span>
          <h2>
            {t("Ready to Build a More Governed")} <br />
            <em>{t("AI Workforce?")}</em>
          </h2>
          <p>
            {t(
              "Temukan bagaimana DEXTRA menyatukan pekerja AI spesialis dan wewenang manusia dalam satu ruang kerja operasional."
            )}
          </p>
          <div className="lp-final__cta">
            <Link className="lp-btn lp-btn--white" href="/login">
              <span>{t("Explore DEXTRA Dashboard")}</span>
              {icon.arrowRight}
            </Link>
            <Link className="lp-btn lp-btn--outline" href="/login">{t("Masuk ke Akun")}</Link>
          </div>
          <div className="lp-final__trust">
            <span>{t("Tanpa data contoh yang dikarang")}</span>
            <em aria-hidden="true">•</em>
            <span>{t("Setiap tindakan lewat mandat")}</span>
            <em aria-hidden="true">•</em>
            <span>{t("Jejak audit permanen")}</span>
          </div>
        </div>
      </section>

      {/* ==================== J. FOOTER ==================== */}
      <footer className="lp-footer">
        <div className="lp-wrap">
          <div className="lp-footer__grid">
            <div className="lp-footer__brand">
              <div className="lp-footer__brand-row">
                <span className="lp-footer__mark">D</span>
                <span className="lp-footer__name">DEXTRA</span>
              </div>
              <p>
                Governed Enterprise AI Workforce &amp; Operations Platform. Specialized AI workers.
                Human-defined authority. Accountable execution.
              </p>
              <div className="lp-footer__principle">
                {t("Prinsip:")} &ldquo;{t("Baca boleh otomatis, tulis harus lewat mandat.")}&rdquo;
              </div>
            </div>

            {FOOTER_COLS.map((column) => (
              <div key={column.title}>
                <h4>{t(column.title)}</h4>
                <ul>
                  {column.links.map((link) => (
                    <li key={`${link.href}-${link.label}`}>
                      <Link href={link.href}>{t(link.label)}</Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="lp-footer__bottom">
            <div>© 2026 DEXTRA. {t("Hak cipta dilindungi.")}</div>
            <div className="lp-footer__links">
              <a href="#governance">{t("Tata kelola")}</a>
              <a href="#workflow">{t("Alur kerja")}</a>
              <a href="#integrations">{t("Integrasi")}</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

