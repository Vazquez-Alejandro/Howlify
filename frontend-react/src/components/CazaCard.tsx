import { useState } from "react";
import { api, type Caza } from "../api/client";
import { useToast } from "./Toast";

interface Props {
  caza: Caza;
  onHunt: () => void;
  onDelete: () => void;
  onUpdate: () => void;
  hunting: boolean;
}

export default function CazaCard({ caza, onHunt, onDelete, onUpdate, hunting }: Props) {
  const { toast } = useToast();
  const [results, setResults] = useState<{ title: string; price: number; url: string }[] | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [loadingResults, setLoadingResults] = useState(false);
  const [showEdit, setShowEdit] = useState(false);

  const [editForm, setEditForm] = useState({
    keyword: caza.producto || caza.keyword || "",
    url: caza.link || caza.url || "",
    precio_max: caza.precio_max,
  });

  const kw = (caza.producto || caza.keyword || "Sin nombre").toUpperCase();
  const url = caza.link || caza.url || "";
  const hasPrice = caza.last_price != null;
  const isAlert = hasPrice && caza.last_price! <= caza.precio_max;

  const handleHunt = async () => {
    setResults(null);
    setLoadingResults(true);
    onHunt();
    const res = await api.huntSingle(caza.id);
    setLoadingResults(false);
    if (res.data?.results) {
      setResults(res.data.results);
      setShowResults(true);
    }
  };

  const handleSave = async () => {
    await api.updateCaza(caza.id, {
      keyword: editForm.keyword,
      url: editForm.url,
      precio_max: editForm.precio_max,
    });
    setShowEdit(false);
    onUpdate();
    toast("Cacería actualizada", "success");
  };

  return (
    <>
      <div className="bg-gray-900/60 backdrop-blur-sm rounded-2xl border border-gray-800/50 p-4 hover:border-gray-700/50 transition-all duration-200">
        <div className="flex items-center justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="text-white font-medium truncate">{kw}</p>
              {isAlert && (
                <span className="shrink-0 px-2 py-0.5 text-xs font-medium bg-red-500/10 text-red-400 rounded-lg border border-red-500/20">
                  ALERTA
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <p className="text-gray-500 text-sm truncate">{url.slice(0, 55)}</p>
            </div>
            <div className="flex items-center gap-3 mt-0.5">
              {hasPrice && (
                <span className={`text-sm font-medium ${isAlert ? "text-red-400" : "text-green-400"}`}>
                  Últ: ${caza.last_price!.toLocaleString()}
                </span>
              )}
              <span className="text-sm text-gray-500">
                Máx: ${caza.precio_max.toLocaleString()}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 ml-4 shrink-0">
            <button
              onClick={handleHunt}
              disabled={hunting || loadingResults}
              className="px-3 py-1.5 bg-gray-800/50 text-gray-400 rounded-xl hover:bg-gray-700/50 hover:text-gray-200 text-sm transition-all border border-gray-700/50 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Olfatear"
            >
              {hunting || loadingResults ? (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              ) : "🐺"}
            </button>
            <button
              onClick={() => {
                setEditForm({
                  keyword: caza.producto || caza.keyword || "",
                  url: caza.link || caza.url || "",
                  precio_max: caza.precio_max,
                });
                setShowEdit(true);
              }}
              className="px-3 py-1.5 bg-gray-800/50 text-gray-600 rounded-xl hover:bg-blue-900/30 hover:text-blue-400 text-sm transition-all border border-gray-700/50"
              title="Editar"
            >
              ✏️
            </button>
            <button
              onClick={onDelete}
              className="px-3 py-1.5 bg-gray-800/50 text-gray-600 rounded-xl hover:bg-red-900/30 hover:text-red-400 text-sm transition-all border border-gray-700/50"
              title="Eliminar"
            >
              🗑️
            </button>
          </div>
        </div>

        {loadingResults && (
          <div className="mt-3 pt-3 border-t border-gray-800/50">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <svg className="animate-spin h-4 w-4 text-red-500" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              Olfateando...
            </div>
          </div>
        )}

        {results && showResults && results.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-800/50">
            <div className="flex items-center justify-between mb-2">
              <button
                onClick={() => setShowResults(false)}
                className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                Ocultar resultados
              </button>
              <span className="text-xs text-gray-500">{results.length} resultado{results.length !== 1 ? "s" : ""}</span>
            </div>
            <div className="space-y-1">
              {results.slice(0, 5).map((r, i) => (
                <div key={i} className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-gray-800/30 transition-colors">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500/50 shrink-0" />
                    <span className="text-gray-300 text-sm truncate">{r.title?.slice(0, 65)}</span>
                  </div>
                  <span className="text-green-400 font-medium text-sm ml-3 shrink-0">${(r.price || 0).toLocaleString()}</span>
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-3 px-2.5 py-1 bg-gray-800/50 text-gray-400 rounded-lg text-xs hover:bg-gray-700/50 hover:text-gray-200 transition-all border border-gray-700/50 shrink-0"
                  >
                    Ver
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {results && showResults && results.length === 0 && (
          <div className="mt-3 pt-3 border-t border-gray-800/50">
            <p className="text-sm text-gray-500">Sin resultados en esta ronda</p>
          </div>
        )}
      </div>

      {showEdit && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={() => setShowEdit(false)}>
          <div className="bg-gray-900 rounded-2xl border border-gray-800/50 p-6 w-full max-w-md mx-4 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-white mb-4">✏️ Editar cacería</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-400 ml-1 uppercase">Producto / Keyword</label>
                <input value={editForm.keyword} onChange={e => setEditForm(f => ({ ...f, keyword: e.target.value }))}
                  className="w-full mt-0.5 px-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white text-sm focus:outline-none focus:border-red-500/50" />
              </div>
              <div>
                <label className="text-xs text-gray-400 ml-1 uppercase">URL</label>
                <input value={editForm.url} onChange={e => setEditForm(f => ({ ...f, url: e.target.value }))}
                  className="w-full mt-0.5 px-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white text-sm focus:outline-none focus:border-red-500/50" />
              </div>
              <div>
                <label className="text-xs text-gray-400 ml-1 uppercase">Precio máximo</label>
                <input type="number" value={editForm.precio_max} onChange={e => setEditForm(f => ({ ...f, precio_max: Number(e.target.value) }))}
                  className="w-full mt-0.5 px-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-white text-sm focus:outline-none focus:border-red-500/50" />
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={() => setShowEdit(false)} className="flex-1 py-2 bg-gray-800 text-gray-400 rounded-lg text-sm font-medium hover:bg-gray-700 transition-all">Cancelar</button>
              <button onClick={handleSave} className="flex-1 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg text-sm font-semibold hover:from-red-600 hover:to-red-700 transition-all shadow-lg shadow-red-500/20">💾 Guardar</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
