import "./globals.css";
import type { Metadata } from "next";
import localFont from "next/font/local";
import Script from "next/script";
import type { ReactNode } from "react";

const GA_MEASUREMENT_ID = "G-52XYZ9ZD0J";

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
      <body>
        {children}
        <Script
          src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`}
          strategy="afterInteractive"
        />
        <Script id="google-analytics" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){window.dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', '${GA_MEASUREMENT_ID}');
          `}
        </Script>
      </body>
    </html>
  );
}
