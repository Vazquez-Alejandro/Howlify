import { type CSSProperties } from "react";
import logo from "../assets/logo.png";

interface Props {
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
}

const sizes = { sm: 12, md: 20, lg: 28, xl: 36 };

const circleClip: CSSProperties = {
  clipPath: "circle(50%)",
  WebkitClipPath: "circle(50%)",
};

export default function Logo({ size = "md", className = "" }: Props) {
  const px = sizes[size];
  const dim = px * 4;

  return (
    <div
      className={`relative inline-flex items-center justify-center shrink-0 ${className}`}
      style={{ width: dim, height: dim }}
    >
      <div
        className="absolute bg-gradient-to-br from-red-500/20 to-red-700/20 blur-2xl"
        style={{ inset: 0, ...circleClip, transform: "scale(1.5)" }}
      />
      <div className="relative w-full h-full" style={circleClip}>
        <img
          src={logo}
          alt="Howlify"
          className="w-full h-full"
          style={{ objectFit: "cover", display: "block" }}
        />
      </div>
    </div>
  );
}
