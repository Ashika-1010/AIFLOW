import { useState, useEffect } from 'react';

/**
 * Animate a numeric value counting up or down over duration ms.
 */
export function useCountUp(target: number, duration: number = 600, decimals: number = 0): number {
  const [current, setCurrent] = useState<number>(target);

  useEffect(() => {
    let startTimestamp: number | null = null;
    const initial = current;
    const diff = target - initial;

    if (diff === 0) return;

    let animationFrameId: number;

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      
      // Ease out cubic
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const val = initial + diff * easeOut;

      const factor = Math.pow(10, decimals);
      setCurrent(Math.round(val * factor) / factor);

      if (progress < 1) {
        animationFrameId = window.requestAnimationFrame(step);
      } else {
        setCurrent(target);
      }
    };

    animationFrameId = window.requestAnimationFrame(step);

    return () => {
      window.cancelAnimationFrame(animationFrameId);
    };
  }, [target, duration, decimals]);

  return current;
}
