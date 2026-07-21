import type { CSSProperties, InputHTMLAttributes } from "react";

interface SliderProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "min" | "max" | "value"> {
  min?: number;
  max?: number;
  value: number;
}

/**
 * Range input whose track is filled up to the current value (bright white,
 * via --color-slider-fill / --range-fill in globals.css).
 */
export function Slider({ min = 0, max = 100, value, style, ...props }: SliderProps) {
  const range = max - min;
  const percent = range > 0 ? ((value - min) / range) * 100 : 0;
  const fillStyle: CSSProperties = {
    ...style,
    ["--range-fill" as string]: `${Math.min(100, Math.max(0, percent))}%`,
  };

  return <input type="range" min={min} max={max} value={value} style={fillStyle} {...props} />;
}
