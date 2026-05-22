import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useToast } from "../components/Toast";
import { traducirError } from "../utils/errors";
import PageTransition from "../components/PageTransition";

const PLAN_LABELS: Record<string, string> = {
  starter: "Starter",
  pro: "Pro",
  business_reseller: "Business Reseller",
  business_monitor: "Business Monitor",
};

export default function ProfilePage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [profile, setProfile] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);

  const [telegramId, setTelegramId] = useState("");
  const [whatsapp, setWhatsapp] = useState("");

  useEffect(() => {
    api.getProfile().then((res) => {
      if (res.data?.profile) {
        setProfile(res.data.profile);
        setTelegramId((res.data.profile.telegram_id as string) || "");
        setWhatsapp((res.data.profile.whatsapp_number as string) || "");
      }
      setLoading(false);
    });
  }, []);

  const saveProfile = async () => {
    setSaving(true);
    const res = await api.updateProfile({
      telegram_id: telegramId || null,
      whatsapp_number: whatsapp || null,
    });
    if (res.error) toast(traducirError(res.error), "error");
    else toast("Perfil actualizado", "success");
    setSaving(false);
  };

  const testChannel = async (channel: string) => {
    setTesting(channel);
    const res = await api.testNotification(channel);
    if (res.error) toast(traducirError(res.error), "error");
    else if (res.data?.ok) toast(`✅ Notificación enviada por ${channel}`, "success");
    else toast(`❌ Error enviando por ${channel}`, "error");
    setTesting(null);
  };

  if (loading) {
    return (
      <PageTransition>
        <div className="p-8 text-gray-400">Cargando perfil...</div>
      </PageTransition>
    );
  }

  const plan = (profile.plan as string) || "starter";

  return (
    <PageTransition>
      <div className="max-w-2xl mx-auto space-y-8">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate("/dashboard")} className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-xl transition-all" title="Volver">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          </button>
          <h1 className="text-2xl font-bold text-white">Configuración</h1>
        </div>

        {/* Plan */}
        <section className="bg-gray-900/60 rounded-2xl p-6 space-y-4" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
          <h2 className="text-lg font-semibold text-white">Mi Plan</h2>
          <div className="flex items-center justify-between">
            <div>
              <span className="text-red-400 font-medium">{PLAN_LABELS[plan] || plan}</span>
              <p className="text-sm text-gray-500 mt-1">
                {profile.email as string}
              </p>
            </div>
            <span className="text-xs bg-gray-800 text-gray-400 px-3 py-1 rounded-full">
              {plan}
            </span>
          </div>
        </section>

        {/* Notificaciones */}
        <section className="bg-gray-900/60 rounded-2xl p-6 space-y-6" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
          <h2 className="text-lg font-semibold text-white">Notificaciones</h2>

          {/* Telegram */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-gray-300">Telegram</label>
            <div className="flex gap-2">
              <input
                type="text" placeholder="ID de Telegram (ej: 123456789)"
                value={telegramId}
                onChange={(e) => setTelegramId(e.target.value)}
                className="flex-1 px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 text-sm"
              />
              <button
                onClick={() => testChannel("telegram")}
                disabled={testing === "telegram" || !telegramId}
                className="px-4 py-2.5 bg-gray-800 border border-gray-700 text-gray-300 rounded-xl text-sm hover:bg-gray-700 disabled:opacity-40"
              >
                {testing === "telegram" ? "..." : "Probar"}
              </button>
            </div>
          </div>

          {/* WhatsApp */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-gray-300">WhatsApp</label>
            <div className="flex gap-2">
              <input
                type="text" placeholder="Número (ej: 541155582107)"
                value={whatsapp}
                onChange={(e) => setWhatsapp(e.target.value)}
                className="flex-1 px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 text-sm"
              />
              <button
                onClick={() => testChannel("whatsapp")}
                disabled={testing === "whatsapp" || !whatsapp}
                className="px-4 py-2.5 bg-gray-800 border border-gray-700 text-gray-300 rounded-xl text-sm hover:bg-gray-700 disabled:opacity-40"
              >
                {testing === "whatsapp" ? "..." : "Probar"}
              </button>
            </div>
          </div>

          {/* Email test */}
          <div className="flex items-center justify-between pt-2">
            <span className="text-sm text-gray-400">
              Email: {profile.email as string}
            </span>
            <button
              onClick={() => testChannel("email")}
              disabled={testing === "email"}
              className="px-4 py-2 bg-gray-800 border border-gray-700 text-gray-300 rounded-xl text-sm hover:bg-gray-700 disabled:opacity-40"
            >
              {testing === "email" ? "..." : "Probar Email"}
            </button>
          </div>

          <button
            onClick={saveProfile}
            disabled={saving}
            className="w-full py-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold text-sm hover:from-red-600 hover:to-red-700 disabled:opacity-50 transition-all"
          >
            {saving ? "Guardando..." : "Guardar configuración"}
          </button>
        </section>
      </div>
    </PageTransition>
  );
}
