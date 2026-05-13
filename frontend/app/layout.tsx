import "./globals.css";
import type { Metadata } from "next";
import localFont from "next/font/local";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Talent Signal",
  description: "Talent Signal 猎头酒馆，追踪公开岗位变化与公司招聘信号。",
  icons: {
    icon: "/talent-signal-icon-32.svg",
    shortcut: "/talent-signal-icon-32.svg",
    apple: "/talent-signal-icon-32.svg",
  },
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
