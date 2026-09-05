"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, AlertCircle, FileText, ActivitySquare, ShieldCheck, Settings, LayoutDashboard } from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();

  const navGroups = [
    {
      title: "OVERVIEW",
      items: [
        { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      ],
    },
    {
      title: "RECOVERY",
      items: [
        { name: "Cases", href: "/cases", icon: FileText },
        { name: "Recovery Actions", href: "/actions", icon: ActivitySquare },
        { name: "Human Review", href: "/review", icon: AlertCircle },
      ],
    },
    {
      title: "SYSTEM",
      items: [
        { name: "Audit Logs", href: "/audit", icon: Activity },
        { name: "System Status", href: "/status", icon: ShieldCheck },
        { name: "Settings", href: "/settings", icon: Settings },
      ],
    },
  ];

  return (
    <aside className="fixed inset-y-0 left-0 z-20 flex w-64 flex-col border-r border-border bg-background">
      <div className="flex h-16 shrink-0 items-center px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-accent-blue/10 text-accent-blue">
            <ShieldCheck size={20} />
          </div>
          <div>
            <div className="text-sm font-bold leading-none text-primary">Razorpay</div>
            <div className="text-[10px] font-mono tracking-widest text-accent-blue uppercase mt-1">AI Recovery</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-4 py-6">
        {navGroups.map((group) => (
          <div key={group.title} className="mb-8">
            <h3 className="mb-3 px-2 text-xs font-semibold tracking-wider text-tertiary">
              {group.title}
            </h3>
            <div className="space-y-1">
              {group.items.map((item) => {
                const isActive = pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                      isActive
                        ? "bg-accent-blue/10 text-accent-blue font-medium"
                        : "text-secondary hover:bg-surfaceHover hover:text-primary"
                    }`}
                  >
                    <item.icon size={18} className={isActive ? "text-accent-blue" : "text-tertiary"} />
                    {item.name}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 px-2 py-2">
          <div className="h-2 w-2 rounded-full bg-accent-green"></div>
          <span className="text-xs font-mono text-tertiary">SYSTEM ONLINE • v4.2.0</span>
        </div>
      </div>
    </aside>
  );
}
