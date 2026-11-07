import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DEXTRA — Governed Enterprise AI Workforce & Operations Platform',
  description:
    'Intelligent enterprise operating system coordinating specialized AI agents with human-in-the-loop governance, ERP operations, HR management, and audit traceability.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
