"use client";

import { useState, useCallback, useEffect } from "react";

interface Particle {
  id: number;
  x: number;
  y: number;
  color: string;
  size: number;
  angle: number;
  distance: number;
  duration: number;
}

interface FeedbackEffectsProps {
  trigger: boolean;
  x: number;
  y: number;
  type?: 'bloom' | 'dewdrop' | 'sparkle';
}

export function FeedbackEffects({ trigger, x, y, type = 'bloom' }: FeedbackEffectsProps) {
  const [particles, setParticles] = useState<Particle[]>([]);

  useEffect(() => {
    if (trigger) {
      createParticles();
    }
  }, [trigger]);

  const createParticles = useCallback(() => {
    const colors = [
      '#3b82f6', // blue-500
      '#60a5fa', // blue-400
      '#93c5fd', // blue-300
      '#bfdbfe', // blue-200
      '#dbeafe', // blue-100
    ];
    
    const newParticles: Particle[] = [];
    const count = type === 'bloom' ? 8 : type === 'dewdrop' ? 5 : 6;
    
    for (let i = 0; i < count; i++) {
      newParticles.push({
        id: Date.now() + i,
        x,
        y,
        color: colors[Math.floor(Math.random() * colors.length)],
        size: 4 + Math.random() * 4,
        angle: (360 / count) * i + Math.random() * 30,
        distance: 30 + Math.random() * 40,
        duration: 600 + Math.random() * 400,
      });
    }
    
    setParticles(newParticles);
    
    // 清理粒子
    setTimeout(() => {
      setParticles([]);
    }, 1200);
  }, [x, y, type]);

  if (particles.length === 0) return null;

  return (
    <div className="fixed inset-0 pointer-events-none z-[100]">
      {particles.map((particle) => (
        <ParticleElement key={particle.id} particle={particle} type={type} />
      ))}
    </div>
  );
}

function ParticleElement({ particle, type }: { particle: Particle; type: string }) {
  const radian = (particle.angle * Math.PI) / 180;
  const endX = particle.x + Math.cos(radian) * particle.distance;
  const endY = particle.y + Math.sin(radian) * particle.distance;

  return (
    <div
      className="absolute animate-particle-bloom"
      style={{
        left: particle.x,
        top: particle.y,
        '--end-x': `${endX - particle.x}px`,
        '--end-y': `${endY - particle.y}px`,
        animationDuration: `${particle.duration}ms`,
      } as React.CSSProperties}
    >
      <div
        className={`
          rounded-full
          ${type === 'sparkle' ? 'animate-pulse' : ''}
        `}
        style={{
          width: particle.size,
          height: particle.size,
          backgroundColor: particle.color,
          boxShadow: `0 0 ${particle.size * 2}px ${particle.color}50`,
        }}
      />
    </div>
  );
}

// 全局反馈管理
interface FeedbackItem {
  id: number;
  x: number;
  y: number;
  type: 'bloom' | 'dewdrop' | 'sparkle';
}

export function useFeedback() {
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([]);

  const triggerFeedback = useCallback((x: number, y: number, type: 'bloom' | 'dewdrop' | 'sparkle' = 'bloom') => {
    const id = Date.now();
    setFeedbacks(prev => [...prev, { id, x, y, type }]);
    
    setTimeout(() => {
      setFeedbacks(prev => prev.filter(f => f.id !== id));
    }, 1500);
  }, []);

  const FeedbackContainer = useCallback(() => (
    <>
      {feedbacks.map(feedback => (
        <FeedbackEffects
          key={feedback.id}
          trigger={true}
          x={feedback.x}
          y={feedback.y}
          type={feedback.type}
        />
      ))}
    </>
  ), [feedbacks]);

  return { triggerFeedback, FeedbackContainer };
}
