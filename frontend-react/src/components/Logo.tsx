import logo from "../assets/logo.png";

interface Props {
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
}

const sizes = { sm: 14, md: 32, lg: 40, xl: 48 };

const maskStyle = {
  maskImage: "radial-gradient(circle at center, black 30%, transparent 72%)",
  WebkitMaskImage: "radial-gradient(circle at center, black 30%, transparent 72%)",
};

export default function Logo({ size = "md", className = "" }: Props) {
  const px = sizes[size];
  const dim = px * 4;

  return (
    <div
      className={`inline-flex items-center justify-center shrink-0 ${className}`}
      style={{ width: dim, height: dim }}
    >
      <img
        src={logo}
        alt="Howlify"
        className="w-full h-full"
        style={{ objectFit: "cover", display: "block", ...maskStyle }}
      />
    </div>
  );
}
