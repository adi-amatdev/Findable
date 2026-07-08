import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Findable — AI Readiness Audit",
  description: "See how AI crawlers read your page. URL in, SiteFacts out.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
