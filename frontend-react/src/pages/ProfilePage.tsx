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

const DAY_LABELS = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

export default function ProfilePage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [profile, setProfile] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);

  const [telegramId, setTelegramId] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [reportEnabled, setReportEnabled] = useState(false);
  const [reportTime, setReportTime] = useState("09:00");
  const [reportDays, setReportDays] = useState<number[]>([1, 2, 3, 4, 5]);

  useEffect(() => {
    api.getProfile().then((res) => {
      if (res.data?.profile) {
        const p = res.data.profile;
        setProfile(p);
        setTelegramId((p.telegram_id as string) || "");
        setWhatsapp((p.whatsapp_number as string) || "");
        setEmailNotifications(p.email_notifications !== false);
        setReportEnabled(p.report_enabled === true);
        setReportTime((p.report_time as string) || "09:00");
        setReportDays(Array.isArray(p.report_days) ? p.report_days : [1, 2, 3, 4, 5]);
      }
      setLoading(false);
    });
  }, []);

  const saveProfile = async () => {
    setSaving(true);
    const res = await api.updateProfile({
      telegram_id: telegramId || null,
      whatsapp_number: whatsapp || null,
      email_notifications: emailNotifications,
      report_enabled: reportEnabled,
      report_time: reportTime,
      report_days: reportDays,
    });
    if (res.error) toast(traducirError(res.error), "error");
    else toast("Perfil actualizado", "success");
    setSaving(false);
  };

  const testChannel = async (channel: string) => {
    setTesting(channel);
    const res = await api.testNotification({ canal: channel });
    if (res.error) toast(traducirError(res.error), "error");
    else toast(`Notificación enviada por ${channel}`, "success");
    setTesting(null);
  };

  const toggleDay = (day: number) => {
    setReportDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day].sort()
    );
  };

  if (loading) {
    return (
      <PageTransition>
        <div className="p-8 text-gray-400">Cargando perfil...</div>
      </PageTransition>
    );
  }

  const plan = (profile.plan as string) || "starter";
  const isStarter = plan === "starter";

  return (
    <PageTransition>
      <div className="max-w-2xl mx-auto space-y-8">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate("/dashboard")} className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-xl transition-all" title="Volver">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          </button>
          <h1 className="text-2xl font-bold text-white">Configuración</h1>
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
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-300">WhatsApp</label>
              {isStarter && (
                <span className="text-[10px] bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded-full border border-amber-500/20">
                  Solo planes Pro y Business
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <input
                type="text" placeholder="Número (ej: 541155582107)"
                value={whatsapp}
                onChange={(e) => setWhatsapp(e.target.value)}
                disabled={isStarter}
                className="flex-1 px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 text-sm disabled:opacity-40"
              />
              <button
                onClick={() => testChannel("whatsapp")}
                disabled={testing === "whatsapp" || !whatsapp || isStarter}
                className="px-4 py-2.5 bg-gray-800 border border-gray-700 text-gray-300 rounded-xl text-sm hover:bg-gray-700 disabled:opacity-40"
              >
                {testing === "whatsapp" ? "..." : "Probar"}
              </button>
            </div>
            {isStarter && (
              <p className="text-[11px] text-gray-600">Actualizate a Pro o Business para recibir alertas por WhatsApp.</p>
            )}
          </div>

          {/* Email */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-300">Email</label>
                <p className="text-xs text-gray-500 mt-0.5">{profile.email as string}</p>
              </div>
              <button
                onClick={() => testChannel("email")}
                disabled={testing === "email"}
                className="px-4 py-2 bg-gray-800 border border-gray-700 text-gray-300 rounded-xl text-sm hover:bg-gray-700 disabled:opacity-40"
              >
                {testing === "email" ? "..." : "Probar"}
              </button>
            </div>
            <label className="flex items-center gap-3 cursor-pointer">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={emailNotifications}
                  onChange={(e) => setEmailNotifications(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-gray-700 rounded-full peer peer-checked:bg-red-500 transition-colors" />
                <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
              </div>
              <span className="text-sm text-gray-400">Recibir notificaciones por email</span>
            </label>
          </div>

          <button
            onClick={saveProfile}
            disabled={saving}
            className="w-full py-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl font-semibold text-sm hover:from-red-600 hover:to-red-700 disabled:opacity-50 transition-all"
          >
            {saving ? "Guardando..." : "Guardar configuración"}
          </button>
        </section>

        {/* Reportes programados */}
        <section className="bg-gray-900/60 rounded-2xl p-6 space-y-5" style={{border: '1px solid rgba(107,114,128,0.4)'}}>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Reportes programados</h2>
            <label className="relative cursor-pointer">
              <input
                type="checkbox"
                checked={reportEnabled}
                onChange={(e) => setReportEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-gray-700 rounded-full peer peer-checked:bg-red-500 transition-colors" />
              <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
            </label>
          </div>

          {reportEnabled && (
            <>
              <p className="text-sm text-gray-400">Recibí un resumen periódico de tus productos, alertas y violaciones MAP.</p>

              {/* Horario */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">Horario</label>
                <input
                  type="time"
                  value={reportTime}
                  onChange={(e) => setReportTime(e.target.value)}
                  className="px-4 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:border-red-500/50 text-sm"
                />
              </div>

              {/* Días */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">Días de envío</label>
                <div className="flex gap-2">
                  {DAY_LABELS.map((label, i) => (
                    <button
                      key={i}
                      onClick={() => toggleDay(i)}
                      className={`w-10 h-10 rounded-xl text-xs font-medium transition-all ${
                        reportDays.includes(i)
                          ? "bg-red-500/20 text-red-400 border border-red-500/30"
                          : "bg-gray-800/50 text-gray-500 border border-gray-700/50 hover:border-gray-600"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </PageTransition>
  );
}
