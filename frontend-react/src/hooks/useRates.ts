import { useState, useEffect } from "react";
import { api } from "../api/client";

interface Rates {
  blue: number;
  tarjeta: number;
  oficial: number;
}

let cached: Rates | null = null;
let promise: Promise<Rates | null> | null = null;

function fetchRates(): Promise<Rates | null> {
  if (cached) return Promise.resolve(cached);
  if (promise) return promise;
  promise = api.get<{ blue: number; tarjeta: number; oficial: number }>("/api/rates")
    .then(res => {
      if (res.data) {
        cached = { blue: res.data.blue, tarjeta: res.data.tarjeta, oficial: res.data.oficial };
        return cached;
      }
      return null;
    })
    .catch(() => null)
    .finally(() => { promise = null; });
  return promise;
}

export function useRates() {
  const [rates, setRates] = useState<Rates | null>(cached);
  const [showUsd, setShowUsd] = useState(() => localStorage.getItem("show_usd") === "true");

  useEffect(() => {
    if (!rates) fetchRates().then(setRates);
  }, []);

  useEffect(() => {
    localStorage.setItem("show_usd", String(showUsd));
  }, [showUsd]);

  const formatARS = (amount: number) =>
    amount.toLocaleString("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 0 });

  const formatUSD = (amount: number, rateType: keyof Rates = "blue") => {
    if (!rates || !rates[rateType]) return "";
    const usd = amount / rates[rateType];
    return usd.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
  };

  const formatPrice = (amount: number, rateType: keyof Rates = "blue") => {
    if (!amount) return "-";
    const ars = formatARS(amount);
    if (!showUsd || !rates) return ars;
    return `${ars} (${formatUSD(amount, rateType)} USD)`;
  };

  const shortPrice = (amount: number) => {
    if (!amount) return "-";
    if (!showUsd || !rates) return `$${amount.toLocaleString()}`;
    const usd = amount / rates.blue;
    return `$${amount.toLocaleString()} · $${Math.round(usd).toLocaleString()} USD`;
  };

  return { rates, showUsd, setShowUsd, formatPrice, shortPrice, formatARS, formatUSD };
}
