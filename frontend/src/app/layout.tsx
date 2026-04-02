import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pacific Container Co. — AI Sales Assistant",
  description: "Get instant answers about shipping containers, pricing, and delivery.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased bg-gray-100 min-h-screen">{children}</body>
    </html>
  );
}
