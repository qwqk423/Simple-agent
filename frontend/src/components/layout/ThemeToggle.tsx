"use client";

import { Sun, Moon, Monitor } from "lucide-react";
import { useApp } from "@/lib/store";
import type { Theme } from "@/lib/store";

export function ThemeToggle() {
  const { theme, setTheme, isDark } = useApp();

  const themes: { value: Theme; icon: React.ReactNode; label: string }[] = [
    { value: "light", icon: <Sun className="w-4 h-4" />, label: "浅色" },
    { value: "dark", icon: <Moon className="w-4 h-4" />, label: "深色" },
    { value: "system", icon: <Monitor className="w-4 h-4" />, label: "自动" },
  ];

  return (
    <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-full">
      {themes.map(({ value, icon, label }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          className={`
            relative p-2 rounded-full transition-all duration-300
            ${theme === value 
              ? 'text-primary-foreground' 
              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }
          `}
          title={label}
        >
          {theme === value && (
            <span 
              className={`
                absolute inset-0 rounded-full 
                ${isDark ? 'bg-primary/80' : 'bg-primary'}
                animate-fade-in-scale
              `} 
            />
          )}
          <span className="relative z-10">{icon}</span>
        </button>
      ))}
    </div>
  );
}
