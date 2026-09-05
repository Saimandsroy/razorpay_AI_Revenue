import type { Metadata } from "next";
import "./globals.css";

import { Sidebar } from "./components/Sidebar";

export const metadata: Metadata = {
  title: "Razorpay AI Recovery",
  description: "Revenue Recovery Intelligence Command Center",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="bg-background text-primary antialiased">
        <Sidebar />
        <div className="pl-64">
          <div className="min-h-screen">
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
