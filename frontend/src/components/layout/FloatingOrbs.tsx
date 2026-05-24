"use client";

import { useEffect, useState } from "react";
import { useApp } from "@/lib/store";

interface Orb {
  id: number;
  x: number;
  y: number;
  size: number;
  duration: number;
  delay: number;
  color: string;
}

export function FloatingOrbs() {
  const { isDark } = useApp();
  const [orbs, setOrbs] = useState<Orb[]>([]);

  useEffect(() => {
    // 生成随机光斑
    const generateOrbs = () => {
      const colors = isDark 
        ? [
            "rgba(59, 130, 246, 0.15)",   // blue
            "rgba(96, 165, 250, 0.12)",   // light blue
            "rgba(147, 197, 253, 0.1)",   // lighter blue
            "rgba(224, 242, 254, 0.08)",  // sky
          ]
        : [
            "rgba(59, 130, 246, 0.18)",   // blue
            "rgba(96, 165, 250, 0.15)",   // light blue
            "rgba(147, 197, 253, 0.22)",  // lighter blue
            "rgba(224, 242, 254, 0.25)",  // sky
            "rgba(219, 234, 254, 0.2)",   // blue tint
          ];
      
      const newOrbs: Orb[] = [];
      const count = isDark ? 5 : 6;
      
      for (let i = 0; i < count; i++) {
        newOrbs.push({
          id: i,
          x: Math.random() * 100,
          y: Math.random() * 100,
          size: 150 + Math.random() * 250,
          duration: 20 + Math.random() * 20,
          delay: Math.random() * 10,
          color: colors[Math.floor(Math.random() * colors.length)],
        });
      }
      
      setOrbs(newOrbs);
    };

    generateOrbs();
  }, [isDark]);

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {orbs.map((orb) => (
        <div
          key={orb.id}
          className="absolute rounded-full blur-3xl animate-float"
          style={{
            left: `${orb.x}%`,
            top: `${orb.y}%`,
            width: orb.size,
            height: orb.size,
            background: `radial-gradient(circle, ${orb.color} 0%, transparent 70%)`,
            animationDuration: `${orb.duration}s`,
            animationDelay: `${orb.delay}s`,
            transform: "translate(-50%, -50%)",
          }}
        />
      ))}
      
      {/* 额外的装饰光点 */}
      <div className="absolute top-1/4 left-1/4 w-2 h-2 rounded-full bg-blue-400/30 animate-pulse-soft" />
      <div className="absolute top-3/4 right-1/3 w-1.5 h-1.5 rounded-full bg-sky-400/30 animate-pulse-soft" style={{ animationDelay: "1s" }} />
      <div className="absolute bottom-1/3 left-1/2 w-1 h-1 rounded-full bg-blue-300/40 animate-pulse-soft" style={{ animationDelay: "2s" }} />
      <div className="absolute top-1/2 right-1/4 w-2 h-2 rounded-full bg-sky-300/30 animate-pulse-soft" style={{ animationDelay: "0.5s" }} />
    </div>
  );
}
