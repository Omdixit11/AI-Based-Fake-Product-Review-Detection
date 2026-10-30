import type { Metadata, Viewport } from "next";
import { Space_Grotesk, Inter, JetBrains_Mono } from "next/font/google";
import "@/styles/globals.css";
import { ThemeProvider, ToastProvider } from "./providers";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { CommandPalette } from "@/components/layout/command-palette";

const grotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-grotesk",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "TruthLens — Fake Review Detection",
    template: "%s · TruthLens",
  },
  description:
    "Forensic-grade AI that tells whether a product review is fake or genuine — with explainable evidence, not a black box.",
};

export const viewport: Viewport = {
  themeColor: "#07080C",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${grotesk.variable} ${inter.variable} ${jetbrains.variable} grain min-h-screen font-sans antialiased`}
      >
        <ThemeProvider>
          <ToastProvider>
            {/* Aurora backdrop + dotted grid */}
            <div className="aurora-bg dot-grid" aria-hidden>
              <div className="aurora-drift-layer" />
            </div>
            <a
              href="#main"
              className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-lg focus:bg-elevate focus:px-4 focus:py-2 focus:text-sm focus:text-ink"
            >
              Skip to content
            </a>
            <Navbar />
            <CommandPalette />
            <main id="main" className="relative pt-28 md:pt-32">
              {children}
            </main>
            <Footer />
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
