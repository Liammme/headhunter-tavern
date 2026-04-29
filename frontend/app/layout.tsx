import "./globals.css";
import type { Metadata } from "next";
import localFont from "next/font/local";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Talent Signal",
  description: "AI talent market signal dashboard",
};

const headingFont = localFont({
  src: "./fonts/Kalam-Bold.ttf",
  variable: "--font-heading",
  display: "swap",
});

const bodyFont = localFont({
  src: "./fonts/PatrickHand-Regular.ttf",
  variable: "--font-body",
  display: "swap",
});

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN" className={`${headingFont.variable} ${bodyFont.variable}`}>
      <body>{children}</body>
    </html>
  );
}
