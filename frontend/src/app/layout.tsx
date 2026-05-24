import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/lib/store";

export const metadata: Metadata = {
  title: "Simple Agent",
  description: "轻量级、全透明的 AI Agent 系统",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        {/* Favicon - 蓝色渐变背景 + Sparkles 星星图标 */}
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs><linearGradient id='bg' x1='0%25' y1='0%25' x2='100%25' y2='100%25'><stop offset='0%25' style='stop-color:%233b82f6'/><stop offset='100%25' style='stop-color:%232563eb'/></linearGradient></defs><rect width='100' height='100' rx='22' fill='url(%23bg)'/><g transform='translate(50,50)' fill='none' stroke='white' stroke-width='7' stroke-linecap='round' stroke-linejoin='round'><path d='M0,-18 C0,-10 -10,-6 -10,0 C-10,6 0,10 0,18 C0,10 10,6 10,0 C10,-6 0,-10 0,-18 Z'/><path d='M-18,-18 L-10,-10'/><path d='M18,-18 L10,-10'/><path d='M-18,18 L-10,10'/><path d='M18,18 L10,10'/></g></svg>" />
        {/* Google Fonts - Inter & Playfair Display */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link 
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;600;700&family=Noto+Serif+SC:wght@400;500;600;700&display=swap" 
          rel="stylesheet" 
        />
      </head>
      <body className="font-sans antialiased theme-transition">
        <AppProvider>
          {children}
        </AppProvider>
      </body>
    </html>
  );
}
