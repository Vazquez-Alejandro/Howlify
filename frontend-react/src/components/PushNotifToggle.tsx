import { useState, useEffect } from "react";
import { api } from "../api/client";
import { useToast } from "./Toast";

function urlBase64ToUint8Array(base64: string) {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const b64 = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(b64), c => c.charCodeAt(0));
}

const VAPID_PUBLIC_KEY = "BFOsu1BnpmQw_fTfZkxVv38EwaFSjBv-1YPit7OxRACkWZWe22_yh2ZuqsooC5OSKieZcIRe3KthzvAWhPVT3ak";

export default function PushNotifToggle() {
  const { toast } = useToast();
  const [subscribed, setSubscribed] = useState(false);
  const [supported, setSupported] = useState(false);

  useEffect(() => {
    if ("serviceWorker" in navigator && "PushManager" in window) {
      setSupported(true);
      navigator.serviceWorker.ready.then(reg => {
        reg.pushManager.getSubscription().then(sub => setSubscribed(!!sub));
      });
    }
  }, []);

  const subscribe = async () => {
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
      });
      await api.post("/api/push/subscribe", { subscription: sub.toJSON() });
      setSubscribed(true);
      toast("Notificaciones push activadas", "success");
    } catch {
      toast("No se pudieron activar las notificaciones", "error");
    }
  };

  const unsubscribe = async () => {
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      await sub?.unsubscribe();
      await api.del("/api/push/subscribe");
      setSubscribed(false);
      toast("Notificaciones push desactivadas", "success");
    } catch {
      toast("Error al desactivar", "error");
    }
  };

  if (!supported) return null;

  return (
    <button onClick={subscribed ? unsubscribe : subscribe}
      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all border flex items-center gap-1.5 ${subscribed ? "bg-green-500/15 text-green-400 border-green-500/30" : "bg-gray-800/50 text-gray-400 border-gray-700/50"}`}>
      {subscribed ? "🔔 Push activado" : "🔕 Activar push"}
    </button>
  );
}
