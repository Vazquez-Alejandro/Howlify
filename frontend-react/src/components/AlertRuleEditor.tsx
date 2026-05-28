import { useState } from "react";
import type { AlertRule } from "../api/client";

const RULE_TYPES = [
  { value: "pct_drop", label: "Baja %", desc: "Cuando el precio baja un % respecto al último" },
  { value: "below_price", label: "Precio mínimo", desc: "Cuando el precio baja de este valor" },
  { value: "above_price", label: "Precio máximo", desc: "Cuando el precio supera este valor" },
  { value: "consecutive_drop", label: "Bajas consecutivas", desc: "Cuando baja N veces seguidas" },
  { value: "velocity_drop", label: "Caída rápida", desc: "Cuando baja más de X% en 24hs" },
  { value: "below_hist_min", label: "Mínimo histórico", desc: "Cuando alcanza un nuevo mínimo" },
  { value: "restock", label: "Reposición", desc: "Cuando vuelve a estar disponible" },
];

const CHANNELS = [
  { value: "push", label: "🔔 Push" },
  { value: "whatsapp", label: "💬 WhatsApp" },
  { value: "telegram", label: "✈️ Telegram" },
  { value: "email", label: "📧 Email" },
  { value: "all", label: "📢 Todos" },
];

function genId() {
  return crypto.randomUUID();
}

interface Props {
  rules: AlertRule[];
  onChange: (rules: AlertRule[]) => void;
}

export default function AlertRuleEditor({ rules, onChange }: Props) {
  const [showForm, setShowForm] = useState(false);
  const [newRule, setNewRule] = useState<Partial<AlertRule>>({ type: "pct_drop", threshold: 10, channel: "push", cooldown: 60, enabled: true });

  const addRule = () => {
    if (!newRule.type || !newRule.threshold) return;
    onChange([...rules, { id: genId(), type: newRule.type as AlertRule["type"], threshold: newRule.threshold, channel: newRule.channel as AlertRule["channel"], cooldown: newRule.cooldown || 60, enabled: true }]);
    setShowForm(false);
    setNewRule({ type: "pct_drop", threshold: 10, channel: "push", cooldown: 60, enabled: true });
  };

  const removeRule = (id: string) => onChange(rules.filter(r => r.id !== id));
  const toggleRule = (id: string) => onChange(rules.map(r => r.id === id ? { ...r, enabled: !r.enabled } : r));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Alertas inteligentes</h4>
        <button onClick={() => setShowForm(!showForm)} className="text-xs text-blue-400 hover:text-blue-300 transition-colors">
          {showForm ? "Cancelar" : "+ Agregar"}
        </button>
      </div>

      {rules.length === 0 && !showForm && (
        <p className="text-xs text-gray-500 italic">Sin reglas configuradas. Agregá una para recibir alertas personalizadas.</p>
      )}

      {rules.map(r => {
        const t = RULE_TYPES.find(t => t.value === r.type);
        return (
          <div key={r.id} className={`flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-lg text-xs transition-all ${r.enabled ? "bg-gray-800/50 border border-gray-700/50" : "bg-gray-900/30 border border-gray-800/30 opacity-50"}`}>
            <div className="flex items-center gap-2 min-w-0">
              <button onClick={() => toggleRule(r.id)} className="shrink-0 text-sm">{r.enabled ? "🟢" : "⚪"}</button>
              <div className="min-w-0">
                <span className="text-gray-200 font-medium">{t?.label || r.type}</span>
                <span className="text-gray-500 ml-1.5">
                  {r.type === "pct_drop" && `> ${r.threshold}%`}
                  {r.type === "below_price" && `< $${r.threshold}`}
                  {r.type === "above_price" && `> $${r.threshold}`}
                  {r.type === "consecutive_drop" && `${r.threshold} veces`}
                  {r.type === "velocity_drop" && `> ${r.threshold}%`}
                  {r.type === "below_hist_min" && "⚡"}
                  {r.type === "restock" && "📦"}
                </span>
                <span className="text-gray-600 ml-1.5">· {CHANNELS.find(c => c.value === r.channel)?.label || r.channel}</span>
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <span className="text-gray-600 text-[10px]">{r.cooldown}min</span>
              <button onClick={() => removeRule(r.id)} className="text-gray-600 hover:text-red-400 transition-colors ml-1">✕</button>
            </div>
          </div>
        );
      })}

      {showForm && (
        <div className="bg-gray-800/30 border border-gray-700/50 rounded-lg p-3 space-y-2.5">
          <div className="grid grid-cols-2 gap-2">
            {RULE_TYPES.map(t => (
              <button key={t.value} onClick={() => setNewRule({ ...newRule, type: t.value as AlertRule["type"] })}
                className={`text-left px-2 py-1.5 rounded-lg text-xs transition-all border ${newRule.type === t.value ? "bg-blue-500/15 text-blue-400 border-blue-500/30" : "bg-gray-800/50 text-gray-400 border-gray-700/50 hover:border-gray-600"}`}>
                <div className="font-medium">{t.label}</div>
                <div className="text-[10px] text-gray-500 mt-0.5">{t.desc}</div>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 shrink-0">Umbral:</label>
            <input type="number" value={newRule.threshold || ""} onChange={e => setNewRule({ ...newRule, threshold: Number(e.target.value) })}
              className="w-20 px-2 py-1 bg-gray-800/50 border border-gray-700/50 rounded-lg text-xs text-gray-200 focus:outline-none focus:border-blue-500/50" />
            <label className="text-xs text-gray-400 shrink-0 ml-2">Canal:</label>
            <select value={newRule.channel} onChange={e => setNewRule({ ...newRule, channel: e.target.value as AlertRule["channel"] })}
              className="px-2 py-1 bg-gray-800/50 border border-gray-700/50 rounded-lg text-xs text-gray-200 focus:outline-none focus:border-blue-500/50">
              {CHANNELS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
            <label className="text-xs text-gray-400 shrink-0 ml-2">Cooldown:</label>
            <select value={newRule.cooldown} onChange={e => setNewRule({ ...newRule, cooldown: Number(e.target.value) })}
              className="px-2 py-1 bg-gray-800/50 border border-gray-700/50 rounded-lg text-xs text-gray-200 focus:outline-none focus:border-blue-500/50">
              <option value={15}>15 min</option>
              <option value={30}>30 min</option>
              <option value={60}>1 hora</option>
              <option value={120}>2 horas</option>
              <option value={360}>6 horas</option>
              <option value={1440}>24 horas</option>
            </select>
          </div>

          <button onClick={addRule} className="w-full py-1.5 bg-blue-500/20 text-blue-400 rounded-lg text-xs font-medium hover:bg-blue-500/30 transition-all border border-blue-500/30">
            + Agregar regla
          </button>
        </div>
      )}
    </div>
  );
}
