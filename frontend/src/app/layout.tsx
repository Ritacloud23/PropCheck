import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: { default: "PropCheck Nigeria — verify before you pay rent", template: "%s · PropCheck Nigeria" },
  description:
    "Find verified agents and verified rental properties in Lagos, Rivers, Enugu, Anambra and Imo. See exactly what was checked before you pay rent.",
  metadataBase: new URL(process.env.FRONTEND_URL ?? "http://localhost:3000"),
};

export const viewport: Viewport = { themeColor: "#15803d", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en-NG" className={inter.variable}>
      <body className="min-h-dvh font-sans">{children}</body>
    </html>
  );
}
