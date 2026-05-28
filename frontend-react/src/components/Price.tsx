import { useRates } from "../hooks/useRates";

export default function Price({ amount, className = "" }: { amount: number; className?: string }) {
  const { showUsd, rates } = useRates();
  if (!amount || amount <= 0) return <span className={className}>-</span>;
  return (
    <span className={className} title={showUsd && rates ? `${(amount / rates.blue).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 })} USD (blue)` : undefined}>
      ${amount.toLocaleString()}
      {showUsd && rates && (
        <span className="text-[10px] text-gray-500 ml-1 font-normal">
          USD {Math.round(amount / rates.blue).toLocaleString()}
        </span>
      )}
    </span>
  );
}
