import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, keyStore, currentKey, type Health, type PublicConfig } from "./api";

type ToastKind = "ok" | "err" | "info";
interface Toast {
  id: number;
  text: string;
  kind: ToastKind;
}

interface AppState {
  config: PublicConfig | null;
  health: Health | null;
  apiKey: string | null;
  keySource: "custom" | "demo" | null;
  setApiKey: (key: string | null) => void;
  keyDialog: boolean;
  openKeyDialog: (open: boolean) => void;
  toast: (text: string, kind?: ToastKind) => void;
}

const Ctx = createContext<AppState | null>(null);
let toastId = 1;

export function AppProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [apiKey, setKey] = useState<string | null>(currentKey());
  const [keyDialog, openKeyDialog] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((text: string, kind: ToastKind = "info") => {
    const id = toastId++;
    setToasts((t) => [...t.slice(-3), { id, text, kind }]);
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500);
  }, []);

  const setApiKey = useCallback((key: string | null) => {
    keyStore.set(key);
    setKey(key);
  }, []);

  useEffect(() => {
    api
      .config()
      .then((c) => {
        setConfig(c);
        // First visit on a public deployment: use the rate-limited demo key
        if (!currentKey() && c.demo_api_key) setApiKey(c.demo_api_key);
        else if (!currentKey()) openKeyDialog(true);
      })
      .catch(() => setConfig(null));

    const poll = () => api.health().then(setHealth).catch(() => setHealth(null));
    poll();
    const t = window.setInterval(poll, 15000);
    return () => window.clearInterval(t);
  }, [setApiKey]);

  const value = useMemo<AppState>(
    () => ({
      config,
      health,
      apiKey,
      keySource: !apiKey ? null : apiKey === config?.demo_api_key ? "demo" : "custom",
      setApiKey,
      keyDialog,
      openKeyDialog,
      toast,
    }),
    [config, health, apiKey, setApiKey, keyDialog, toast],
  );

  return (
    <Ctx.Provider value={value}>
      {children}
      <div style={{ position: "fixed", right: 20, bottom: 20, display: "flex", flexDirection: "column", gap: 8, zIndex: 60 }}
           role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className="panel" style={{
            padding: "12px 16px", fontSize: 14, maxWidth: 380,
            borderLeft: `3px solid ${t.kind === "err" ? "var(--critical)" : t.kind === "ok" ? "var(--good)" : "var(--accent)"}`,
          }}>
            {t.text}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useApp() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useApp outside AppProvider");
  return ctx;
}
