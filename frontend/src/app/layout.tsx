import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ORCA — Marine Intelligence Platform',
  description:
    'Agentic AI marine decision-support system. Real-time safety assessment, PFZ detection, route optimisation and proactive hazard monitoring.',
  keywords: ['marine safety', 'ISRO', 'fishing zone', 'ocean intelligence', 'ORCA'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />

      </head>
      <body className="h-full overflow-hidden" suppressHydrationWarning>{children}</body>
    </html>
  );
}
