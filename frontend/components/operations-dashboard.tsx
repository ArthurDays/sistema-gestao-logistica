"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";

// Cada rota reutiliza o mesmo shell e os mesmos painéis operacionais, exibindo apenas seu domínio.
export type DashboardView = "overview" | "catalog" | "finances" | "fleet";

type Vehicle = {
  id: string;
  name: string;
  category: string;
  odometer_km: string;
  status: string;
  plate?: string | null;
  model?: string | null;
  catalog_spec_id?: string | null;
};

type Profitability = {
  vehicle_id: string;
  gross_revenue: string;
  fuel_cost: string;
  other_expenses: string;
  maintenance_reserve: string;
  total_cost: string;
  net_profit: string;
};

type MonthlyDashboard = {
  gross_revenue: string;
  fuel_cost: string;
  maintenance_cost: string;
  net_profit: string;
};

type ExpensePeriod = {
  period: "day" | "week" | "month";
  date_from: string;
  date_to: string;
  fuel_cost: string;
  maintenance_cost: string;
  other_expenses: string;
  total_cost: string;
  fuel_percent: string;
  maintenance_percent: string;
  other_percent: string;
};

type CatalogSpec = {
  id: string;
  category: string;
  brand: string;
  model: string;
  version: string;
  powertrain: string;
  model_year: string;
  fuel_type: string;
  gasoline_consumption_km_l: string | null;
  ethanol_consumption_km_l: string | null;
  tank_capacity_l: string | null;
  estimated_tank_cost: string | null;
  oil_change_km: number | null;
  oil_change_cost: string | null;
  tire_change_km: number | null;
  synced_at: string;
};

type MaintenanceRule = {
  id: string;
  vehicle_id: string;
  name: string;
  interval_km: string | null;
  interval_days: number | null;
  estimated_cost: string;
  warning_km: string;
  warning_days: number;
};

type MaintenanceAlert = {
  id: string;
  vehicle_id: string;
  rule_id: string;
  severity: "warning" | "critical";
  due_odometer_km: string | null;
  due_date: string | null;
  message: string;
};

type FleetTotals = {
  revenue: number;
  fuel: number;
  maintenance: number;
  other: number;
  net: number;
};

type UserSession = {
  user_id: string;
  organization_id: string;
  organization_name: string;
  email: string;
  role: "operator" | "manager" | "admin";
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

const categoryNames: Record<string, string> = {
  motorcycle: "Moto",
  car: "Carro",
  truck: "Caminhão",
  bus: "Ônibus",
  bicycle: "Bicicleta",
  other: "Outro",
};

async function apiFetch(path: string, init: RequestInit = {}) {
  const token = window.localStorage.getItem("access_token");
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });
  if (response.status === 401) {
    window.localStorage.removeItem("access_token");
    window.dispatchEvent(new Event("auth:expired"));
  }
  return response;
}

function KpiIcon({ kind }: { kind: "revenue" | "fuel" | "maintenance" | "profit" }) {
  const paths = {
    revenue: <><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></>,
    fuel: <><path d="M3 22h12V3H3zM6 7h6M15 8h2l3 3v7a2 2 0 0 1-4 0v-4" /></>,
    maintenance: <><path d="m14.7 6.3 3-3a4.2 4.2 0 0 1-5.5 5.5L5 16l3 3 7.2-7.2a4.2 4.2 0 0 1 5.5-5.5l-3 3z" /></>,
    profit: <><path d="M3 17 9 11l4 4 8-9M15 6h6v6" /></>,
  };
  return <svg aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24">{paths[kind]}</svg>;
}

export function OperationsDashboard({ view = "overview" }: { view?: DashboardView }) {
  const [authenticated, setAuthenticated] = useState(() => typeof window !== "undefined" && Boolean(window.localStorage.getItem("access_token")));
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [alerts, setAlerts] = useState<MaintenanceAlert[]>([]);
  const [rules, setRules] = useState<MaintenanceRule[]>([]);
  const [totals, setTotals] = useState<FleetTotals>({ revenue: 0, fuel: 0, maintenance: 0, other: 0, net: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [panelMode, setPanelMode] = useState<"closing" | "maintenance" | "vehicle" | "details" | null>(null);
  const [vehicleFinancials, setVehicleFinancials] = useState<Record<string, Profitability>>({});
  const [selectedVehicleId, setSelectedVehicleId] = useState("");
  const [selectedRuleId, setSelectedRuleId] = useState("");
  const [expensePeriods, setExpensePeriods] = useState<ExpensePeriod[]>([]);
  const [catalogSpecs, setCatalogSpecs] = useState<CatalogSpec[]>([]);
  const [catalogSearch, setCatalogSearch] = useState("");
  const [catalogCategory, setCatalogCategory] = useState("all");
  const [syncingCatalog, setSyncingCatalog] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedCatalogId, setSelectedCatalogId] = useState("");
  const [session, setSession] = useState<UserSession | null>(null);

  useEffect(() => {
    const url = new URL(window.location.href);
    const token = url.searchParams.get("access_token");
    if (!token) return;
    window.localStorage.setItem("access_token", token);
    url.searchParams.delete("access_token");
    window.location.replace(url.toString());
  }, []);

  const signOut = useCallback(() => {
    window.localStorage.removeItem("access_token");
    setAuthenticated(false);
    setSession(null);
    setVehicles([]);
    setAlerts([]);
    setRules([]);
  }, []);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sessionResponse, vehiclesResponse, alertsResponse, rulesResponse, summaryResponse, samplingResponse, catalogResponse] = await Promise.all([
        apiFetch("/api/v1/auth/me", { cache: "no-store" }),
        apiFetch("/api/v1/vehicles", { cache: "no-store" }),
        apiFetch("/api/v1/maintenance-alerts", { cache: "no-store" }),
        apiFetch("/api/v1/maintenance-rules", { cache: "no-store" }),
        apiFetch("/api/v1/dashboard/monthly-summary", { cache: "no-store" }),
        apiFetch("/api/v1/dashboard/expense-sampling", { cache: "no-store" }),
        apiFetch("/api/v1/vehicle-catalog", { cache: "no-store" }),
      ]);
      if (!sessionResponse.ok || !vehiclesResponse.ok || !alertsResponse.ok || !rulesResponse.ok || !summaryResponse.ok || !samplingResponse.ok || !catalogResponse.ok) throw new Error("Não foi possível carregar o painel.");

      const currentSession: UserSession = await sessionResponse.json();
      const fleet: Vehicle[] = await vehiclesResponse.json();
      const fleetAlerts: MaintenanceAlert[] = await alertsResponse.json();
      const maintenanceRules: MaintenanceRule[] = await rulesResponse.json();
      const summary: MonthlyDashboard = await summaryResponse.json();
      const sampling: { periods: ExpensePeriod[] } = await samplingResponse.json();
      const catalog: CatalogSpec[] = await catalogResponse.json();
      const now = new Date();
      const dateFrom = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
      const dateTo = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10);
      const financials = await Promise.all(
        fleet.map(async (vehicle) => {
          const response = await apiFetch(`/api/v1/vehicles/${vehicle.id}/profitability?date_from=${dateFrom}&date_to=${dateTo}`, { cache: "no-store" });
          if (!response.ok) throw new Error("Resumo financeiro indisponível.");
          return response.json() as Promise<Profitability>;
        }),
      );

      setSession(currentSession);
      setVehicles(fleet);
      setAlerts(fleetAlerts);
      setRules(maintenanceRules);
      setExpensePeriods(sampling.periods);
      setCatalogSpecs(catalog);
      setVehicleFinancials(Object.fromEntries(financials.map((item) => [item.vehicle_id, item])));
      const otherExpenses = financials.reduce((sum, item) => sum + Number(item.other_expenses), 0);
      setTotals({
        revenue: Number(summary.gross_revenue),
        fuel: Number(summary.fuel_cost),
        maintenance: Number(summary.maintenance_cost),
        other: otherExpenses,
        net: Number(summary.net_profit),
      });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authenticated) return;
    const loadTimer = window.setTimeout(() => void loadDashboard(), 0);
    return () => window.clearTimeout(loadTimer);
  }, [authenticated, loadDashboard]);
  useEffect(() => {
    window.addEventListener("auth:expired", signOut);
    return () => window.removeEventListener("auth:expired", signOut);
  }, [signOut]);

  async function synchronizeCatalog() {
    setSyncingCatalog(true);
    setError(null);
    try {
      const response = await apiFetch("/api/v1/vehicle-catalog/sync", { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Falha ao sincronizar a planilha.");
      setNotice(`Catálogo sincronizado: ${result.total} modelos (${result.imported} novos).`);
      await loadDashboard();
    } catch (syncError) {
      setError(syncError instanceof Error ? syncError.message : "Falha ao sincronizar a planilha.");
    } finally {
      setSyncingCatalog(false);
    }
  }

  function openClosing(vehicleId?: string) {
    setSelectedVehicleId(vehicleId ?? activeFleet[0]?.id ?? "");
    setPanelMode("closing");
  }

  function openVehicleDetails(vehicleId: string) {
    setSelectedVehicleId(vehicleId);
    setPanelMode("details");
  }

  function openMaintenance(alert: MaintenanceAlert) {
    setSelectedVehicleId(alert.vehicle_id);
    setSelectedRuleId(alert.rule_id);
    setPanelMode("maintenance");
  }

  function openVehicleRegistration(catalogId?: string) {
    setSelectedCatalogId(catalogId ?? catalogSpecs[0]?.id ?? "");
    setPanelMode("vehicle");
  }

  async function submitVehicleRegistration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const response = await apiFetch(`/api/v1/vehicle-catalog/${selectedCatalogId}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: form.get("vehicle_name") || null,
        plate: form.get("plate") || null,
        odometer_km: form.get("initial_odometer_km"),
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      setError(result.detail ?? "Não foi possível cadastrar o veículo.");
      return;
    }
    await loadDashboard();
    setSelectedVehicleId(result.id);
    setPanelMode("closing");
    setNotice(`${result.name} adicionado à frota. Informe agora o hodômetro final do dia.`);
  }

  async function submitClosing(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const response = await apiFetch(`/api/v1/vehicles/${selectedVehicleId}/operations`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({
        operation_date: form.get("operation_date"),
        odometer_end_km: form.get("odometer_end_km"),
        gross_revenue: form.get("gross_revenue"),
        fuel_cost: form.get("fuel_cost"),
        notes: form.get("notes") || null,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      setError(result.detail ?? "Não foi possível lançar o fechamento.");
      return;
    }
    setPanelMode(null);
    setNotice(
      `Fechamento registrado: ${result.odometer_start_km} → ${result.odometer_end_km} km `
      + `(${result.distance_km} km rodados).`,
    );
    await loadDashboard();
  }

  async function submitMaintenance(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const response = await apiFetch(`/api/v1/maintenance-rules/${selectedRuleId}/executions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        performed_at: form.get("performed_at"),
        odometer_km: form.get("odometer_km"),
        actual_cost: form.get("actual_cost"),
        supplier: form.get("supplier") || null,
        notes: form.get("notes") || null,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      setError(result.detail ?? "Não foi possível registrar a manutenção.");
      return;
    }
    setPanelMode(null);
    setNotice("Manutenção registrada e alertas recalculados.");
    await loadDashboard();
  }

  function exportFleet() {
    const rows = [["Veículo", "Categoria", "Status", "KM atual"], ...vehicles.map((vehicle) => [vehicle.name, categoryNames[vehicle.category] ?? vehicle.category, vehicle.status, vehicle.odometer_km])];
    const csv = rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(";")).join("\n");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" }));
    link.download = `frota-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  const activeFleet = vehicles.filter((vehicle) => vehicle.status === "active");
  const filteredFleet = categoryFilter === "all" ? activeFleet : activeFleet.filter((vehicle) => vehicle.category === categoryFilter);
  const fleetCategories = Object.entries(categoryNames).map(([id, label]) => ({ id, label, count: activeFleet.filter((vehicle) => vehicle.category === id).length })).filter((item) => item.count > 0);
  const filteredCatalog = useMemo(() => {
    const term = catalogSearch.trim().toLocaleLowerCase("pt-BR");
    return catalogSpecs.filter((spec) => {
      const matchesCategory = catalogCategory === "all" || spec.category === catalogCategory;
      const matchesSearch = !term || `${spec.brand} ${spec.model} ${spec.version}`.toLocaleLowerCase("pt-BR").includes(term);
      return matchesCategory && matchesSearch;
    });
  }, [catalogCategory, catalogSearch, catalogSpecs]);
  const vehicleById = useMemo(() => new Map(vehicles.map((vehicle) => [vehicle.id, vehicle])), [vehicles]);
  const ruleById = useMemo(() => new Map(rules.map((rule) => [rule.id, rule])), [rules]);
  const expenseTotal = totals.fuel + totals.maintenance + totals.other;
  const fuelShare = expenseTotal ? (totals.fuel / expenseTotal) * 100 : 33;
  const maintenanceShare = expenseTotal ? (totals.maintenance / expenseTotal) * 100 : 33;
  const panelVehicle = vehicleById.get(selectedVehicleId);
  const panelCatalog = catalogSpecs.find((spec) => spec.id === selectedCatalogId);
  const vehicleCatalog = catalogSpecs.find((spec) => spec.id === panelVehicle?.catalog_spec_id);
  const panelFinancial = vehicleFinancials[selectedVehicleId];
  const panelRules = rules.filter((rule) => rule.vehicle_id === selectedVehicleId);
  const panelAlerts = alerts.filter((alert) => alert.vehicle_id === selectedVehicleId);

  const kpis = [
    { label: "Receita bruta", value: totals.revenue, icon: "revenue" as const, iconClass: "bg-slate-100 text-slate-600", valueClass: "text-slate-950" },
    { label: "Custo de combustível", value: totals.fuel, icon: "fuel" as const, iconClass: "bg-amber-50 text-amber-600", valueClass: "text-amber-700" },
    { label: "Desgaste / manutenção", value: totals.maintenance, icon: "maintenance" as const, iconClass: "bg-orange-50 text-orange-600", valueClass: "text-orange-700" },
    { label: "Lucro líquido real", value: totals.net, icon: "profit" as const, iconClass: "bg-emerald-50 text-emerald-600", valueClass: "font-bold text-emerald-600" },
  ];
  const pageCopy = {
    overview: { eyebrow: "VISÃO GERENCIAL", title: "Dashboard executivo", description: "Indicadores essenciais da saúde financeira e operacional da frota." },
    catalog: { eyebrow: "BASE TÉCNICA", title: "Catálogo de veículos", description: "Modelos e especificações sincronizados com a planilha mestre." },
    finances: { eyebrow: "ANÁLISE FINANCEIRA", title: "Receitas e custos", description: "Acompanhe lucro real, combustível, manutenção e composição dos gastos." },
    fleet: { eyebrow: "OPERAÇÃO", title: "Frota e manutenção", description: "Controle veículos, hodômetros, fechamentos e alertas preventivos." },
  }[view];

  if (!authenticated) return <LoginForm onAuthenticated={() => setAuthenticated(true)} />;

  return (
    <div className="min-h-screen bg-[#f5f7fb]">
      <DashboardSidebar activeSection={view} alerts={alerts.length} collapsed={sidebarCollapsed} mobileOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} onSignOut={signOut} onToggle={() => setSidebarCollapsed((current) => !current)} session={session} syncing={syncingCatalog} />
      <main className={`min-h-screen bg-[#f5f7fb] px-4 pb-28 pt-6 text-slate-900 transition-[padding] duration-300 sm:px-6 lg:px-8 lg:pb-8 ${sidebarCollapsed ? "lg:pl-28" : "lg:pl-72"}`}>
      <div className="mx-auto max-w-7xl scroll-mt-6" id="overview">
        <header className="-mx-4 -mt-6 mb-6 flex flex-col gap-5 rounded-b-[2rem] bg-gradient-to-br from-[#031329] via-[#06254a] to-[#073b68] px-4 pb-8 pt-6 text-white shadow-xl shadow-blue-950/10 sm:-mx-6 sm:px-6 lg:mx-0 lg:mt-0 lg:mb-8 lg:flex-row lg:items-center lg:justify-between lg:rounded-none lg:bg-none lg:p-0 lg:text-slate-900 lg:shadow-none">
          <div className="flex items-start gap-3">
            <button aria-label="Abrir menu" className="mt-0.5 grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-white/15 bg-white/10 text-white shadow-sm lg:hidden" onClick={() => setSidebarOpen(true)} type="button"><MenuIcon /></button>
            <div>
            <p className="mb-1 text-xs font-bold tracking-[0.18em] text-blue-300 lg:text-blue-600">{pageCopy.eyebrow}</p>
            <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl lg:text-slate-950">{view === "overview" ? `Olá, ${session?.role === "admin" ? "Administrador" : session?.role === "manager" ? "Gestor" : "Operador"} 👋` : pageCopy.title}</h1>
            <p className="mt-2 max-w-xl text-sm text-blue-100/75 lg:text-slate-500">{pageCopy.description}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            {view === "fleet" && <button className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50" onClick={exportFleet} type="button">
              <DownloadIcon /> Exportar frota
            </button>}
            {/* Este botão abre um Slide-over, mantendo o dashboard principal limpo. */}
            <button className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-950/20 transition hover:brightness-110 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 sm:flex-none" onClick={() => openClosing()} type="button">
              <span className="text-lg leading-none">+</span> Lançar fechamento
            </button>
          </div>
        </header>

        {error && <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">{error} <button className="ml-2 underline" onClick={() => void loadDashboard()} type="button">Tentar novamente</button></div>}
        {notice && <div className="mb-6 flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700"><span>{notice}</span><button aria-label="Fechar aviso" onClick={() => setNotice(null)} type="button">×</button></div>}

        {view === "fleet" && <section aria-label="Classificação da frota" className="mb-6 rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-100">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="font-semibold text-slate-900">Classificação da frota</h2>
              <p className="mt-1 text-sm text-slate-500">Filtre o painel operacional pelo tipo de transporte.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <CategoryButton active={categoryFilter === "all"} count={activeFleet.length} label="Todos" onClick={() => setCategoryFilter("all")} />
              {fleetCategories.map((category) => <CategoryButton active={categoryFilter === category.id} count={category.count} key={category.id} label={category.label} onClick={() => setCategoryFilter(category.id)} />)}
            </div>
          </div>
        </section>}

        {view === "catalog" && <section aria-label="Catálogo técnico da planilha" className="mb-6 overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-slate-100">
          <div className="border-b border-slate-100 p-6">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold text-slate-900">Catálogo técnico de veículos</h2><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-emerald-700">Google Sheets</span></div>
                <p className="mt-1 text-sm text-slate-500">Consumo, tanque e ciclos de manutenção espelhados da planilha mestre.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <a className="rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-50" href="https://docs.google.com/spreadsheets/d/1J8YAtNSqD0se5pJVzgBDnggN7lKF37HPnQlbqL9vSOw/edit?gid=521676479#gid=521676479" rel="noreferrer" target="_blank">Abrir planilha ↗</a>
                <button className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-wait disabled:opacity-60" disabled={syncingCatalog} onClick={() => void synchronizeCatalog()} type="button">{syncingCatalog ? "Sincronizando..." : "Atualizar da planilha"}</button>
              </div>
            </div>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap gap-2"><CategoryButton active={catalogCategory === "all"} count={catalogSpecs.length} label="Todos" onClick={() => setCatalogCategory("all")} />{["Carro", "Moto"].map((category) => <CategoryButton active={catalogCategory === category} count={catalogSpecs.filter((spec) => spec.category === category).length} key={category} label={category} onClick={() => setCatalogCategory(category)} />)}</div>
              <div className="relative w-full sm:max-w-xs"><SearchIcon /><input className="w-full rounded-lg border border-slate-200 py-2.5 pl-10 pr-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100" onChange={(event) => setCatalogSearch(event.target.value)} placeholder="Buscar marca ou modelo" type="search" value={catalogSearch} /></div>
            </div>
          </div>
          <div className="hidden max-h-96 overflow-auto sm:block">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="sticky top-0 z-10 bg-slate-50"><tr>{["Veículo", "Combustível / consumo", "Tanque", "Troca de óleo", "Troca de pneu", "Ação"].map((heading) => <th className="whitespace-nowrap px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500" key={heading}>{heading}</th>)}</tr></thead>
              <tbody className="divide-y divide-slate-100">
                {filteredCatalog.map((spec) => <tr className="hover:bg-slate-50" key={spec.id}><td className="min-w-64 px-6 py-4"><strong className="block text-sm text-slate-900">{spec.brand} {spec.model}</strong><span className="mt-1 block text-xs text-slate-500">{spec.version} · {spec.model_year}</span><span className="mt-1 block text-xs text-slate-400">{spec.powertrain}</span></td><td className="whitespace-nowrap px-6 py-4 text-sm text-slate-600"><span className="block">{spec.fuel_type}</span><strong className="mt-1 block text-slate-800">{spec.gasoline_consumption_km_l ? `${spec.gasoline_consumption_km_l} km/l` : "—"}</strong>{spec.ethanol_consumption_km_l && <span className="text-xs text-slate-400">Álcool: {spec.ethanol_consumption_km_l} km/l</span>}</td><td className="whitespace-nowrap px-6 py-4 text-sm"><strong className="block text-slate-800">{spec.tank_capacity_l ? `${spec.tank_capacity_l} L` : "—"}</strong><span className="mt-1 block text-xs text-slate-400">{spec.estimated_tank_cost ? money.format(Number(spec.estimated_tank_cost)) : "Sem estimativa"}</span></td><td className="whitespace-nowrap px-6 py-4 text-sm"><strong className="block text-slate-800">{spec.oil_change_km ? `${number.format(spec.oil_change_km)} km` : "—"}</strong><span className="mt-1 block text-xs text-slate-400">{spec.oil_change_cost ? money.format(Number(spec.oil_change_cost)) : "Sem custo"}</span></td><td className="whitespace-nowrap px-6 py-4 text-sm font-semibold text-slate-700">{spec.tire_change_km ? `${number.format(spec.tire_change_km)} km` : "—"}</td><td className="whitespace-nowrap px-6 py-4"><button className="rounded-lg bg-emerald-50 px-3 py-2 text-xs font-bold text-emerald-700 transition hover:bg-emerald-600 hover:text-white" onClick={() => openVehicleRegistration(spec.id)} type="button">Adicionar à frota</button></td></tr>)}
                {!loading && filteredCatalog.length === 0 && <tr><td className="px-6 py-12 text-center text-sm text-slate-400" colSpan={6}>{catalogSpecs.length ? "Nenhum modelo encontrado." : "Catálogo vazio. Clique em “Atualizar da planilha”."}</td></tr>}
              </tbody>
            </table>
          </div>
          <div className="space-y-3 p-4 sm:hidden">
            {filteredCatalog.map((spec) => <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm" key={spec.id}><div className="flex items-start justify-between gap-3"><div><strong className="text-sm text-slate-950">{spec.brand} {spec.model}</strong><p className="mt-1 text-xs text-slate-500">{spec.version} · {spec.model_year}</p></div><span className="rounded-lg bg-blue-50 p-2 text-blue-600"><SidebarIcon name="catalog" /></span></div><dl className="mt-4 grid grid-cols-2 gap-3 text-xs"><DetailItem label="Combustível" value={spec.fuel_type || "—"} /><DetailItem label="Consumo" value={spec.gasoline_consumption_km_l ? `${spec.gasoline_consumption_km_l} km/l` : "—"} /><DetailItem label="Tanque" value={spec.tank_capacity_l ? `${spec.tank_capacity_l} L` : "—"} /><DetailItem label="Troca de óleo" value={spec.oil_change_km ? `${number.format(spec.oil_change_km)} km` : "—"} /></dl><button className="mt-4 min-h-11 w-full rounded-xl bg-blue-600 px-3 py-2 text-xs font-bold text-white" onClick={() => openVehicleRegistration(spec.id)} type="button">Adicionar à frota</button></article>)}
            {!loading && filteredCatalog.length === 0 && <p className="py-8 text-center text-sm text-slate-400">Nenhum modelo encontrado.</p>}
          </div>
          {catalogSpecs.length > 0 && <div className="flex flex-col gap-1 border-t border-slate-100 bg-slate-50 px-4 py-3 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6"><span>{filteredCatalog.length} de {catalogSpecs.length} modelos</span><span>Última sincronização: {new Date(catalogSpecs[0].synced_at).toLocaleString("pt-BR")}</span></div>}
        </section>}

        {(view === "overview" || view === "finances") && <section aria-label="Indicadores financeiros" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {kpis.map((kpi) => (
            <article className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-100" key={kpi.label}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">{kpi.label}</p>
                  <p className={`mt-3 text-2xl tabular-nums tracking-tight ${kpi.valueClass}`}>{loading ? "—" : money.format(kpi.value)}</p>
                </div>
                <span className={`rounded-lg p-2.5 ${kpi.iconClass}`}><KpiIcon kind={kpi.icon} /></span>
              </div>
              <p className="mt-4 text-xs text-slate-400">Acumulado no mês atual</p>
            </article>
          ))}
        </section>}

        {(view === "overview" || view === "finances") && <section aria-label="Análises financeiras" className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-5">
          <article className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-100 lg:col-span-3">
            <div className="flex items-center justify-between">
              <div><h2 className="font-semibold text-slate-900">Percentual de gastos</h2><p className="mt-1 text-sm text-slate-500">Amostragem do dia, semana e mês atual</p></div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">Colunas empilhadas</span>
            </div>
            <ExpenseColumnChart loading={loading} periods={expensePeriods} />
          </article>

          <article className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-100 lg:col-span-2">
            <div><h2 className="font-semibold text-slate-900">Composição de despesas</h2><p className="mt-1 text-sm text-slate-500">Distribuição no mês atual</p></div>
            <div className="mt-8 flex flex-col items-center gap-8 sm:flex-row lg:flex-col xl:flex-row">
              <div className="grid h-44 w-44 shrink-0 place-items-center rounded-full" style={{ background: `conic-gradient(#f59e0b 0 ${fuelShare}%, #f97316 ${fuelShare}% ${fuelShare + maintenanceShare}%, #94a3b8 ${fuelShare + maintenanceShare}% 100%)` }}>
                <div className="grid h-28 w-28 place-items-center rounded-full bg-white text-center"><div><strong className="block text-lg tabular-nums">{money.format(expenseTotal)}</strong><span className="text-xs text-slate-400">Total</span></div></div>
              </div>
              <div className="w-full space-y-4 text-sm">
                <ExpenseLegend color="bg-amber-500" label="Combustível" value={totals.fuel} />
                <ExpenseLegend color="bg-orange-500" label="Manutenção" value={totals.maintenance} />
                <ExpenseLegend color="bg-slate-400" label="Outros" value={totals.other} />
              </div>
            </div>
          </article>
        </section>}

        {view === "overview" && <section aria-label="Resumo operacional" className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
          <OverviewStatus href="/frota" label="Veículos ativos" tone="emerald" value={activeFleet.length} />
          <OverviewStatus href="/frota" label="Alertas abertos" tone={alerts.length ? "red" : "emerald"} value={alerts.length} />
          <OverviewStatus href="/catalogo" label="Modelos no catálogo" tone="slate" value={catalogSpecs.length} />
        </section>}

        {view === "fleet" && <section aria-label="Operação e alertas" className="grid grid-cols-1 gap-6 lg:grid-cols-5">
          <article className="overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-slate-100 lg:col-span-3">
            <div className="flex items-center justify-between p-6"><div><h2 className="font-semibold text-slate-900">Frota ativa</h2><p className="mt-1 text-sm text-slate-500">Exibindo {filteredFleet.length} de {activeFleet.length} veículo(s)</p></div><span className="h-2.5 w-2.5 rounded-full bg-emerald-500 ring-4 ring-emerald-50" /></div>
            <div className="hidden overflow-x-auto sm:block">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50"><tr>{["Veículo", "Placa / modelo", "Classificação", "KM atual", "Ações"].map((heading) => <th className={`px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 ${heading === "KM atual" || heading === "Ações" ? "text-right" : ""}`} key={heading}>{heading}</th>)}</tr></thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {filteredFleet.map((vehicle) => (
                    <tr className="cursor-pointer transition hover:bg-emerald-50/50 focus-within:bg-emerald-50/50" key={vehicle.id} onClick={() => openVehicleDetails(vehicle.id)}>
                      <td className="whitespace-nowrap px-6 py-4 text-sm font-semibold text-slate-900">{vehicle.name}<span className="mt-1 flex items-center gap-1.5 text-xs font-normal text-emerald-600"><i className="h-1.5 w-1.5 rounded-full bg-emerald-500" />Clique para ver detalhes</span></td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-500"><span className="font-mono text-xs">{vehicle.plate ?? "SEM PLACA"}</span><span className="mx-2 text-slate-300">·</span>{vehicle.model ?? categoryNames[vehicle.category] ?? vehicle.category}</td>
                      <td className="whitespace-nowrap px-6 py-4"><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">{categoryNames[vehicle.category] ?? vehicle.category}</span></td>
                      <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-semibold tabular-nums text-slate-700">{number.format(Number(vehicle.odometer_km))} km</td>
                      <td className="whitespace-nowrap px-6 py-4 text-right"><button className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700" onClick={(event) => { event.stopPropagation(); openClosing(vehicle.id); }} type="button">Fechar dia</button></td>
                    </tr>
                  ))}
                  {!loading && filteredFleet.length === 0 && <tr><td className="px-6 py-10 text-center text-sm text-slate-400" colSpan={5}>Nenhum veículo nesta classificação.</td></tr>}
                </tbody>
              </table>
            </div>
            <div className="space-y-3 p-4 sm:hidden">
              {filteredFleet.map((vehicle) => <button className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition active:scale-[0.99]" key={vehicle.id} onClick={() => openVehicleDetails(vehicle.id)} type="button"><div className="flex items-start justify-between gap-3"><span className="grid h-11 w-11 place-items-center rounded-xl bg-blue-50 text-blue-600"><SidebarIcon name="fleet" /></span><span className="min-w-0 flex-1"><strong className="block truncate text-sm text-slate-950">{vehicle.name}</strong><small className="mt-1 block truncate text-slate-500">{vehicle.plate ?? "SEM PLACA"} · {vehicle.model ?? categoryNames[vehicle.category] ?? vehicle.category}</small></span><span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700">Ativo</span></div><div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3"><span className="text-xs text-slate-500">KM total</span><strong className="text-sm tabular-nums text-slate-800">{number.format(Number(vehicle.odometer_km))} km</strong></div></button>)}
              {!loading && filteredFleet.length === 0 && <p className="py-8 text-center text-sm text-slate-400">Nenhum veículo nesta classificação.</p>}
            </div>
          </article>

          <aside className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-100 lg:col-span-2">
            <div className="flex items-center justify-between"><div><h2 className="font-semibold text-slate-900">Alertas automáticos</h2><p className="mt-1 text-sm text-slate-500">Manutenções próximas e vencidas</p></div><span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-bold text-red-600">{alerts.length}</span></div>
            <div className="mt-6 space-y-3">
              {alerts.map((alert) => {
                const vehicle = vehicleById.get(alert.vehicle_id);
                const remainingKm = alert.due_odometer_km && vehicle ? Number(alert.due_odometer_km) - Number(vehicle.odometer_km) : null;
                const urgent = alert.severity === "critical" || (remainingKm !== null && remainingKm <= 500);
                return <div className={`rounded-lg border-l-4 p-4 ${urgent ? "border-red-500 bg-red-50" : "border-amber-500 bg-amber-50"}`} key={alert.id}><div className="flex gap-3"><UrgencyIcon urgent={urgent} /><div className="min-w-0 flex-1"><p className={`text-sm font-semibold ${urgent ? "text-red-800" : "text-amber-800"}`}>{ruleById.get(alert.rule_id)?.name ?? "Manutenção preventiva"}</p><p className="mt-1 text-sm text-slate-700">{vehicle?.name ?? "Veículo"}</p><p className="mt-2 text-xs font-medium text-slate-500">{remainingKm !== null ? remainingKm <= 0 ? `Vencida há ${number.format(Math.abs(remainingKm))} km` : `Faltam ${number.format(remainingKm)} km` : `Prazo: ${alert.due_date ?? "a definir"}`}</p><button className={`mt-3 text-xs font-bold underline underline-offset-4 ${urgent ? "text-red-700" : "text-amber-700"}`} onClick={() => openMaintenance(alert)} type="button">Registrar serviço</button></div></div></div>;
              })}
              {!loading && alerts.length === 0 && <div className="rounded-lg border border-dashed border-slate-200 px-4 py-10 text-center"><span className="mx-auto mb-3 grid h-9 w-9 place-items-center rounded-full bg-emerald-50 text-emerald-600">✓</span><p className="text-sm font-medium text-slate-700">Frota em dia</p><p className="mt-1 text-xs text-slate-400">Nenhum alerta de manutenção aberto.</p></div>}
            </div>
          </aside>
        </section>}
      </div>

      {panelMode && (
        <div aria-modal="true" className="fixed inset-0 z-50" role="dialog">
          <button aria-label="Fechar painel" className="absolute inset-0 h-full w-full cursor-default bg-slate-950/40 backdrop-blur-[1px]" onClick={() => setPanelMode(null)} type="button" />
          <aside className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 p-6">
              <div><p className="text-xs font-bold uppercase tracking-wider text-emerald-600">{panelMode === "details" ? "Ficha operacional" : "Ação operacional"}</p><h2 className="mt-2 text-xl font-bold text-slate-950">{panelMode === "closing" ? "Lançar fechamento diário" : panelMode === "maintenance" ? "Registrar manutenção" : panelMode === "vehicle" ? "Adicionar veículo à frota" : "Detalhes do veículo"}</h2><p className="mt-1 text-sm text-slate-500">{panelMode === "closing" ? "Selecione o veículo e informe o KM final do dia." : panelMode === "maintenance" ? ruleById.get(selectedRuleId)?.name : panelMode === "vehicle" ? "Use as especificações da planilha mestre." : panelVehicle?.name}</p></div>
              <button aria-label="Fechar" className="grid h-9 w-9 place-items-center rounded-lg text-xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-700" onClick={() => setPanelMode(null)} type="button">×</button>
            </div>

            {panelMode === "closing" ? (
              <form className="flex flex-1 flex-col overflow-y-auto" onSubmit={submitClosing}>
                <div className="flex-1 space-y-5 p-6">
                  <div><div className="mb-2 flex items-center justify-between"><span className="text-sm font-semibold text-slate-700">Veículo</span><button className="text-xs font-bold text-emerald-700 hover:underline" onClick={() => openVehicleRegistration()} type="button">+ Novo da planilha</button></div><select className={inputClass} disabled={activeFleet.length === 0} required value={selectedVehicleId} onChange={(event) => setSelectedVehicleId(event.target.value)}>{activeFleet.length === 0 && <option value="">Cadastre um veículo da planilha</option>}{activeFleet.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.name} · início {number.format(Number(vehicle.odometer_km))} km</option>)}</select></div>
                  <FieldLabel label="Data do fechamento"><input className={inputClass} defaultValue={new Date().toISOString().slice(0, 10)} name="operation_date" required type="date" /></FieldLabel>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <FieldLabel label="Hodômetro inicial"><input className={`${inputClass} cursor-not-allowed bg-slate-100 text-slate-500`} readOnly value={panelVehicle?.odometer_km ?? "0.00"} /></FieldLabel>
                    <FieldLabel label="Hodômetro final"><input className={inputClass} key={panelVehicle?.id} min={panelVehicle?.odometer_km ?? "0"} name="odometer_end_km" placeholder={panelVehicle?.odometer_km ?? "0"} required step="0.01" type="number" /></FieldLabel>
                  </div>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2"><FieldLabel label="Receita bruta"><div className="relative"><span className="absolute left-3 top-3 text-sm text-slate-400">R$</span><input className={`${inputClass} pl-10`} defaultValue="0" min="0" name="gross_revenue" required step="0.01" type="number" /></div></FieldLabel><FieldLabel label="Combustível (0 = automático)"><div className="relative"><span className="absolute left-3 top-3 text-sm text-slate-400">R$</span><input className={`${inputClass} pl-10`} defaultValue="0" min="0" name="fuel_cost" required step="0.01" type="number" /></div></FieldLabel></div>
                  <FieldLabel label="Observação"><textarea className={inputClass} name="notes" placeholder="Rota, turno ou ocorrência" rows={3} /></FieldLabel>
                </div>
                <PanelFooter close={() => setPanelMode(null)} submitLabel="Salvar fechamento" />
              </form>
            ) : panelMode === "maintenance" ? (
              <form className="flex flex-1 flex-col overflow-y-auto" onSubmit={submitMaintenance}>
                <div className="flex-1 space-y-5 p-6">
                  <div className="rounded-lg bg-slate-50 p-4"><p className="text-xs font-medium text-slate-500">Veículo</p><strong className="mt-1 block text-sm text-slate-900">{panelVehicle?.name}</strong><p className="mt-1 text-xs text-slate-500">Hodômetro atual: {number.format(Number(panelVehicle?.odometer_km ?? 0))} km</p></div>
                  <FieldLabel label="Data do serviço"><input className={inputClass} defaultValue={new Date().toISOString().slice(0, 10)} name="performed_at" required type="date" /></FieldLabel>
                  <FieldLabel label="Hodômetro na execução"><input className={inputClass} defaultValue={panelVehicle?.odometer_km} max={panelVehicle?.odometer_km} min="0" name="odometer_km" required step="0.01" type="number" /></FieldLabel>
                  <FieldLabel label="Custo real"><div className="relative"><span className="absolute left-3 top-3 text-sm text-slate-400">R$</span><input className={`${inputClass} pl-10`} defaultValue="0" min="0" name="actual_cost" required step="0.01" type="number" /></div></FieldLabel>
                  <FieldLabel label="Fornecedor"><input className={inputClass} name="supplier" placeholder="Oficina ou prestador" /></FieldLabel>
                  <FieldLabel label="Observação"><textarea className={inputClass} name="notes" rows={3} /></FieldLabel>
                </div>
                <PanelFooter close={() => setPanelMode(null)} submitLabel="Concluir manutenção" />
              </form>
            ) : panelMode === "vehicle" ? (
              <form className="flex flex-1 flex-col overflow-y-auto" onSubmit={submitVehicleRegistration}>
                <div className="flex-1 space-y-5 p-6">
                  <FieldLabel label="Modelo da planilha"><select className={inputClass} required value={selectedCatalogId} onChange={(event) => setSelectedCatalogId(event.target.value)}>{catalogSpecs.map((spec) => <option key={spec.id} value={spec.id}>{spec.brand} {spec.model} · {spec.version}</option>)}</select></FieldLabel>
                  {panelCatalog && <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-4"><strong className="text-sm text-emerald-900">{panelCatalog.brand} {panelCatalog.model}</strong><div className="mt-3 grid grid-cols-2 gap-3 text-xs text-emerald-800"><span>Consumo<br/><b>{panelCatalog.gasoline_consumption_km_l ?? "—"} km/l</b></span><span>Tanque<br/><b>{panelCatalog.tank_capacity_l ?? "—"} L</b></span><span>Óleo<br/><b>{panelCatalog.oil_change_km ? `${number.format(panelCatalog.oil_change_km)} km` : "—"}</b></span><span>Pneus<br/><b>{panelCatalog.tire_change_km ? `${number.format(panelCatalog.tire_change_km)} km` : "—"}</b></span></div></div>}
                  <FieldLabel label="Nome de identificação"><input className={inputClass} name="vehicle_name" placeholder={panelCatalog ? `${panelCatalog.brand} ${panelCatalog.model}` : "Veículo 01"} /></FieldLabel>
                  <FieldLabel label="Placa (opcional)"><input className={`${inputClass} uppercase`} maxLength={12} name="plate" placeholder="ABC1D23" /></FieldLabel>
                  <FieldLabel label="Hodômetro inicial da operação"><input className={inputClass} defaultValue="0" min="0" name="initial_odometer_km" required step="0.01" type="number" /></FieldLabel>
                  <p className="rounded-lg bg-amber-50 p-3 text-xs leading-relaxed text-amber-800">Este KM será o início oficial do veículo. Nos próximos dias, o sistema usará automaticamente o KM final do fechamento anterior.</p>
                </div>
                <PanelFooter close={() => setPanelMode(null)} submitLabel="Adicionar e lançar dia" />
              </form>
            ) : (
              <div className="flex flex-1 flex-col overflow-y-auto">
                <div className="flex-1 space-y-5 p-6">
                  <section className="rounded-xl bg-slate-950 p-5 text-white shadow-sm">
                    <div className="flex items-start justify-between gap-4">
                      <div><span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">{categoryNames[panelVehicle?.category ?? ""] ?? panelVehicle?.category}</span><h3 className="mt-1 text-xl font-bold">{panelVehicle?.name}</h3><p className="mt-1 font-mono text-xs text-slate-400">{panelVehicle?.plate ?? "SEM PLACA"}</p></div>
                      <span className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-bold text-emerald-300">Ativo</span>
                    </div>
                    <div className="mt-5 border-t border-white/10 pt-4"><p className="text-xs text-slate-400">Hodômetro atual</p><strong className="mt-1 block text-2xl tabular-nums">{number.format(Number(panelVehicle?.odometer_km ?? 0))} km</strong></div>
                  </section>

                  <section><h3 className="text-sm font-bold text-slate-900">Resultado no mês</h3><div className="mt-3 grid grid-cols-2 gap-3">
                    <DetailMetric label="Receita bruta" tone="neutral" value={Number(panelFinancial?.gross_revenue ?? 0)} />
                    <DetailMetric label="Combustível" tone="warning" value={Number(panelFinancial?.fuel_cost ?? 0)} />
                    <DetailMetric label="Manutenção" tone="orange" value={Number(panelFinancial?.maintenance_reserve ?? 0)} />
                    <DetailMetric label="Lucro líquido" tone="profit" value={Number(panelFinancial?.net_profit ?? 0)} />
                  </div></section>

                  {vehicleCatalog && <section className="rounded-xl border border-slate-200 p-4"><h3 className="text-sm font-bold text-slate-900">Especificações técnicas</h3><p className="mt-1 text-xs text-slate-500">{vehicleCatalog.brand} {vehicleCatalog.model} · {vehicleCatalog.version} · {vehicleCatalog.model_year}</p><dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-xs"><DetailItem label="Combustível" value={vehicleCatalog.fuel_type || "—"} /><DetailItem label="Consumo gasolina" value={vehicleCatalog.gasoline_consumption_km_l ? `${vehicleCatalog.gasoline_consumption_km_l} km/l` : "—"} /><DetailItem label="Capacidade do tanque" value={vehicleCatalog.tank_capacity_l ? `${vehicleCatalog.tank_capacity_l} L` : "—"} /><DetailItem label="Troca de óleo" value={vehicleCatalog.oil_change_km ? `${number.format(vehicleCatalog.oil_change_km)} km` : "—"} /><DetailItem label="Troca de pneus" value={vehicleCatalog.tire_change_km ? `${number.format(vehicleCatalog.tire_change_km)} km` : "—"} /><DetailItem label="Motorização" value={vehicleCatalog.powertrain || "—"} /></dl></section>}

                  <section><h3 className="text-sm font-bold text-slate-900">Manutenção preventiva</h3><div className="mt-3 space-y-2">{panelRules.map((rule) => <div className="flex items-center justify-between rounded-lg bg-slate-50 p-3" key={rule.id}><div><p className="text-sm font-semibold text-slate-800">{rule.name}</p><p className="mt-0.5 text-xs text-slate-500">{rule.interval_km ? `A cada ${number.format(Number(rule.interval_km))} km` : rule.interval_days ? `A cada ${rule.interval_days} dias` : "Sem intervalo definido"}</p></div><span className="text-xs font-semibold text-slate-600">{money.format(Number(rule.estimated_cost))}</span></div>)}{panelRules.length === 0 && <p className="rounded-lg border border-dashed border-slate-200 p-4 text-center text-xs text-slate-400">Nenhuma regra cadastrada.</p>}</div></section>

                  <section><div className="flex items-center justify-between"><h3 className="text-sm font-bold text-slate-900">Alertas do veículo</h3><span className={`rounded-full px-2 py-0.5 text-xs font-bold ${panelAlerts.length ? "bg-red-50 text-red-600" : "bg-emerald-50 text-emerald-700"}`}>{panelAlerts.length}</span></div><div className="mt-3 space-y-2">{panelAlerts.map((alert) => <div className={`rounded-lg border-l-4 p-3 ${alert.severity === "critical" ? "border-red-500 bg-red-50" : "border-amber-500 bg-amber-50"}`} key={alert.id}><p className="text-sm font-semibold text-slate-800">{ruleById.get(alert.rule_id)?.name ?? "Manutenção"}</p><p className="mt-1 text-xs text-slate-600">{alert.message}</p></div>)}{panelAlerts.length === 0 && <p className="rounded-lg bg-emerald-50 p-4 text-center text-xs font-medium text-emerald-700">Veículo sem alertas abertos.</p>}</div></section>
                </div>
                <div className="sticky bottom-0 flex flex-col-reverse gap-3 border-t border-slate-200 bg-white p-4 sm:flex-row sm:p-6"><button className="min-h-11 flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-600 hover:bg-slate-50" onClick={() => setPanelMode(null)} type="button">Fechar</button><button className="min-h-11 flex-1 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700" disabled={!panelVehicle} onClick={() => panelVehicle && openClosing(panelVehicle.id)} type="button">Lançar fechamento</button></div>
              </div>
            )}
          </aside>
        </div>
      )}
      </main>
    </div>
  );
}

function LoginForm({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [submitting, setSubmitting] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      const endpoint = mode === "register" ? "/api/v1/auth/register" : "/api/v1/auth/token";
      const payload = mode === "register"
        ? { organization_name: form.get("organization_name"), email: form.get("email"), password: form.get("password") }
        : { email: form.get("email"), password: form.get("password") };
      const response = await fetch(`${API_URL}${endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const result = await response.json();
      if (!response.ok) { setError(typeof result.detail === "string" ? result.detail : "Confira os dados informados."); return; }
      window.localStorage.setItem("access_token", result.access_token);
      onAuthenticated();
    } catch {
      setError("A API está indisponível. Tente novamente em instantes.");
    } finally {
      setSubmitting(false);
    }
  }
  const features: { icon: NavIconName; label: string; detail: string }[] = [
    { icon: "routes", label: "Rotas otimizadas", detail: "Mais eficiência em cada entrega." },
    { icon: "dashboard", label: "Controle de KM", detail: "Acompanhe a performance em tempo real." },
    { icon: "security", label: "Dados seguros", detail: "Informações protegidas por organização." },
  ];
  return (
    <main className="min-h-[100dvh] bg-[#031329] lg:grid lg:grid-cols-[1.08fr_0.92fr]">
      <section className="relative hidden min-h-screen overflow-hidden bg-gradient-to-br from-[#020c1d] via-[#062653] to-[#084779] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-24 top-24 h-80 w-80 rounded-full bg-blue-400/20 blur-3xl" />
        <div className="absolute -bottom-28 left-10 h-96 w-96 rounded-full bg-blue-700/25 blur-3xl" />
        <div className="absolute left-1/2 top-1/2 h-[36rem] w-[36rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-blue-400/10" />
        <div className="relative flex items-center gap-4">
          <Image alt="LogiSync" className="h-16 w-16 object-contain" height={64} priority src="/logisync-logo.png" width={64} />
          <div><BrandName className="text-2xl" /><p className="text-xs uppercase tracking-[0.22em] text-blue-100/60">Gestão logística inteligente</p></div>
        </div>
        <div className="relative max-w-xl">
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-blue-300">Operação sincronizada</p>
          <h1 className="mt-4 text-5xl font-bold leading-tight">Rotas, frota e resultados no mesmo ritmo.</h1>
          <p className="mt-5 max-w-lg text-base leading-relaxed text-blue-100/75">Acompanhe quilômetros, custos, manutenção e lucro real em uma experiência segura em qualquer tela.</p>
          <div className="mt-10 space-y-4">
            {features.map((feature) => <div className="flex items-center gap-4" key={feature.label}><span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-blue-500/15 text-blue-300 ring-1 ring-blue-300/15"><SidebarIcon name={feature.icon} /></span><span><strong className="block text-sm text-white">{feature.label}</strong><small className="mt-1 block text-blue-100/60">{feature.detail}</small></span></div>)}
          </div>
        </div>
        <p className="relative text-xs text-blue-200/45">© 2026 LogiSync. Todos os direitos reservados.</p>
      </section>
      <section className="relative flex min-h-[100dvh] flex-col justify-center overflow-hidden bg-[#031329] px-5 py-8 sm:px-10 lg:grid lg:place-items-center lg:bg-[#f5f7fb]">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-80 bg-[radial-gradient(circle_at_50%_10%,rgba(23,107,255,0.28),transparent_65%)] lg:hidden" />
        <div className="relative mx-auto mb-8 text-center lg:hidden">
          <Image alt="LogiSync" className="mx-auto h-24 w-24 object-contain" height={96} priority src="/logisync-logo.png" width={96} />
          <BrandName className="mt-3 text-4xl" />
          <p className="mt-2 text-sm leading-relaxed text-blue-100/70">Gestão inteligente de rotas<br />e desempenho de veículos</p>
        </div>
        <form className="relative mx-auto w-full max-w-md space-y-5 rounded-[1.75rem] bg-white p-6 shadow-2xl shadow-black/20 ring-1 ring-white/10 sm:p-9" onSubmit={submit}>
          <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">{mode === "register" ? "Comece agora" : "Bem-vindo"}</p><h2 className="mt-2 text-2xl font-bold text-slate-950 sm:text-3xl">{mode === "register" ? "Crie sua operação" : "Acesse sua operação"}</h2><p className="mt-2 text-sm text-slate-500">{mode === "register" ? "Você será o administrador da nova organização." : "Entre com o usuário da sua organização."}</p></div>
          {mode === "register" && <FieldLabel label="Nome da empresa ou operação"><input autoComplete="organization" className={inputClass} maxLength={160} minLength={2} name="organization_name" placeholder="Transportadora Horizonte" required /></FieldLabel>}
          <FieldLabel label="E-mail"><input autoComplete="email" className={inputClass} name="email" placeholder="voce@empresa.com" required type="email" /></FieldLabel>
          <FieldLabel label="Senha"><input autoComplete={mode === "register" ? "new-password" : "current-password"} className={inputClass} minLength={mode === "register" ? 12 : 8} name="password" placeholder={mode === "register" ? "Mínimo de 12 caracteres" : "Sua senha"} required type="password" /></FieldLabel>
          {mode === "register" && <label className="flex items-start gap-3 text-xs leading-relaxed text-slate-500"><input className="mt-0.5 h-4 w-4 rounded border-slate-300 accent-blue-600" required type="checkbox" /><span>Confirmo que posso criar esta organização e aceito os termos de uso da plataforma.</span></label>}
          {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}
          <button className="min-h-12 w-full rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 px-4 py-3 font-semibold text-white shadow-lg shadow-blue-700/20 transition hover:brightness-110 disabled:cursor-wait disabled:opacity-60" disabled={submitting} type="submit">{submitting ? "Processando..." : mode === "register" ? "Criar conta e entrar" : "Entrar"}</button>
          <div className="flex items-center gap-3 text-[10px] uppercase tracking-widest text-slate-300"><span className="h-px flex-1 bg-slate-200" />ou<span className="h-px flex-1 bg-slate-200" /></div>
          <a className="block min-h-11 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-center text-sm font-semibold text-slate-700 transition hover:bg-slate-50" href={`${API_URL}/api/v1/auth/google`}><span className="mr-2 font-bold text-blue-500">G</span>Continuar com Google</a>
          <button className="min-h-11 w-full text-center text-sm font-semibold text-blue-600 hover:text-blue-700" onClick={() => { setMode((current) => current === "login" ? "register" : "login"); setError(null); }} type="button">{mode === "register" ? "Já tenho uma conta" : "Não possui conta? Criar conta"}</button>
          <p className="text-center text-xs text-slate-400">Acesso protegido e isolado por organização</p>
        </form>
      </section>
    </main>
  );
}

type NavIconName = "dashboard" | "catalog" | "finance" | "fleet" | "routes" | "security";

function DashboardSidebar({ activeSection, alerts, collapsed, mobileOpen, onClose, onSignOut, onToggle, session, syncing }: { activeSection: DashboardView; alerts: number; collapsed: boolean; mobileOpen: boolean; onClose: () => void; onSignOut: () => void; onToggle: () => void; session: UserSession | null; syncing: boolean }) {
  const items: { id: DashboardView; href: string; label: string; icon: NavIconName; badge?: number }[] = [
    { id: "overview", href: "/", label: "Visão geral", icon: "dashboard" },
    { id: "catalog", href: "/catalogo", label: "Catálogo técnico", icon: "catalog" },
    { id: "finances", href: "/financeiro", label: "Financeiro", icon: "finance" },
    { id: "fleet", href: "/frota", label: "Frota e alertas", icon: "fleet", badge: alerts },
  ];
  return (
    <>
      {mobileOpen && <button aria-label="Fechar menu" className="fixed inset-0 z-40 bg-slate-950/50 backdrop-blur-sm lg:hidden" onClick={onClose} type="button" />}
      <aside className={`fixed inset-y-0 left-0 z-50 flex flex-col bg-slate-950 text-white shadow-2xl transition-all duration-300 ${collapsed ? "w-20" : "w-64"} ${mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}>
        <div className={`flex h-20 items-center border-b border-white/10 ${collapsed ? "justify-center px-3" : "justify-between px-5"}`}>
          <Link className="flex min-w-0 items-center gap-3" href="/" onClick={onClose} title="Ir para visão geral"><Image alt="LogiSync" className="h-11 w-11 shrink-0 object-contain" height={44} src="/logisync-logo.png" width={44} />{!collapsed && <span className="text-left"><BrandName className="text-sm" /><small className="text-xs text-slate-400">Gestão operacional</small></span>}</Link>
          {!collapsed && <button aria-label="Fechar menu" className="grid h-9 w-9 place-items-center rounded-lg text-slate-400 hover:bg-white/10 hover:text-white lg:hidden" onClick={onClose} type="button">×</button>}
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-6">
          {!collapsed && <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">Navegação</p>}
          {items.map((item) => {
            const active = activeSection === item.id;
            return <Link aria-current={active ? "page" : undefined} className={`group relative flex w-full items-center rounded-xl py-3 text-sm font-semibold transition ${collapsed ? "justify-center px-2" : "gap-3 px-3"} ${active ? "bg-blue-600 text-white shadow-lg shadow-blue-950/20" : "text-slate-400 hover:bg-white/10 hover:text-white"}`} href={item.href} key={item.id} onClick={onClose} title={collapsed ? item.label : undefined}><span className="transition-transform group-hover:scale-110"><SidebarIcon name={item.icon} /></span>{!collapsed && <span>{item.label}</span>}{Boolean(item.badge) && <span className={`${collapsed ? "absolute right-1 top-1" : "ml-auto"} rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold text-white`}>{item.badge}</span>}</Link>;
          })}
        </nav>
        <div className="border-t border-white/10 p-3">
          <div className={`mb-2 rounded-xl bg-white/5 py-3 ${collapsed ? "px-2 text-center" : "px-3"}`} title={session?.email ?? "Usuário autenticado"}><span className="block truncate text-xs font-semibold text-slate-200">{collapsed ? session?.email.slice(0, 1).toUpperCase() : session?.email}</span>{!collapsed && <small className="mt-1 block truncate text-[10px] text-slate-500">{session?.organization_name} · {session?.role}</small>}</div>
          <div className={`mb-2 flex items-center rounded-xl bg-white/5 py-3 ${collapsed ? "justify-center px-2" : "gap-3 px-3"}`} title="Sincronização da planilha"><span className={`h-2.5 w-2.5 shrink-0 rounded-full ${syncing ? "animate-pulse bg-amber-400" : "bg-emerald-400"}`} />{!collapsed && <span className="min-w-0"><strong className="block text-xs text-slate-200">Google Sheets</strong><small className="text-[10px] text-slate-500">{syncing ? "Sincronizando..." : "Sincronização ativa"}</small></span>}</div>
          <button aria-label="Sair" className={`mb-2 flex w-full items-center rounded-xl py-2.5 text-xs font-semibold text-slate-400 transition hover:bg-white/10 hover:text-white ${collapsed ? "justify-center px-2" : "gap-2 px-3"}`} onClick={onSignOut} title="Sair" type="button"><span aria-hidden="true">↪</span>{!collapsed && "Sair"}</button>
          <button aria-label={collapsed ? "Expandir menu" : "Recolher menu"} className="hidden w-full items-center justify-center gap-2 rounded-xl py-2.5 text-xs font-semibold text-slate-400 transition hover:bg-white/10 hover:text-white lg:flex" onClick={onToggle} title={collapsed ? "Expandir menu" : "Recolher menu"} type="button"><CollapseIcon collapsed={collapsed} />{!collapsed && "Recolher menu"}</button>
        </div>
      </aside>
      <nav aria-label="Navegação principal móvel" className="safe-area-bottom fixed inset-x-0 bottom-0 z-40 grid grid-cols-4 border-t border-slate-200/80 bg-white/95 px-2 pt-2 shadow-[0_-12px_32px_rgba(15,23,42,0.08)] backdrop-blur-xl lg:hidden">
        {items.map((item) => {
          const active = activeSection === item.id;
          const mobileLabel = { overview: "Início", catalog: "Catálogo", finances: "Financeiro", fleet: "Frota" }[item.id];
          return <Link aria-current={active ? "page" : undefined} className={`relative flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl px-1 text-[10px] font-semibold transition ${active ? "bg-blue-50 text-blue-600" : "text-slate-500"}`} href={item.href} key={item.id} onClick={onClose}><span className={active ? "scale-110" : ""}><SidebarIcon name={item.icon} /></span><span>{mobileLabel}</span>{Boolean(item.badge) && <span className="absolute right-2 top-1 rounded-full bg-red-500 px-1.5 py-0.5 text-[9px] font-bold text-white">{item.badge}</span>}</Link>;
        })}
      </nav>
    </>
  );
}

function SidebarIcon({ name }: { name: NavIconName }) {
  const paths = {
    dashboard: <><rect height="7" rx="1" width="7" x="3" y="3" /><rect height="7" rx="1" width="7" x="14" y="3" /><rect height="7" rx="1" width="7" x="3" y="14" /><rect height="7" rx="1" width="7" x="14" y="14" /></>,
    catalog: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z" /><path d="M4 5.5v16M8 7h8M8 11h6" /></>,
    finance: <><path d="M4 19V9M10 19V5M16 19v-7M22 19H2" /><path d="m3 6 6-3 6 4 6-4" /></>,
    fleet: <><path d="M3 16V8l2-3h11l3 5v6M5 16h14M6 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM17 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM3 10h16" /></>,
    routes: <><circle cx="6" cy="18" r="2" /><circle cx="18" cy="6" r="2" /><path d="M8 18h2a4 4 0 0 0 4-4v-4a4 4 0 0 1 4-4" /><path d="m15 3 3 3-3 3" /></>,
    security: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /><path d="m9 12 2 2 4-4" /></>,
  };
  return <svg aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24">{paths[name]}</svg>;
}

function BrandName({ className = "" }: { className?: string }) {
  return <strong className={`block tracking-tight text-white ${className}`}>Logi<span className="text-blue-400">Sync</span></strong>;
}

function CollapseIcon({ collapsed }: { collapsed: boolean }) {
  return <svg aria-hidden="true" className={`h-4 w-4 transition-transform ${collapsed ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24"><path d="m15 18-6-6 6-6" /></svg>;
}

function MenuIcon() {
  return <svg aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="2" viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16" /></svg>;
}

const inputClass = "min-h-11 w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

function OverviewStatus({ href, label, tone, value }: { href: string; label: string; tone: "emerald" | "red" | "slate"; value: number }) {
  const tones = { emerald: "bg-emerald-50 text-emerald-700", red: "bg-red-50 text-red-700", slate: "bg-slate-100 text-slate-700" };
  return <Link className="group flex items-center justify-between rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-100 transition hover:-translate-y-0.5 hover:shadow-md" href={href}><div><p className="text-sm font-medium text-slate-500">{label}</p><strong className="mt-2 block text-2xl tabular-nums text-slate-950">{value}</strong></div><span className={`grid h-10 w-10 place-items-center rounded-full text-lg font-bold ${tones[tone]}`}>→</span></Link>;
}

function DetailMetric({ label, tone, value }: { label: string; tone: "neutral" | "warning" | "orange" | "profit"; value: number }) {
  const tones = { neutral: "bg-slate-50 text-slate-900", warning: "bg-amber-50 text-amber-700", orange: "bg-orange-50 text-orange-700", profit: "bg-emerald-50 text-emerald-700" };
  return <div className={`rounded-lg p-3 ${tones[tone]}`}><p className="text-[11px] font-medium opacity-70">{label}</p><strong className="mt-1 block text-sm tabular-nums">{money.format(value)}</strong></div>;
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-slate-400">{label}</dt><dd className="mt-1 font-semibold text-slate-700">{value}</dd></div>;
}

function FieldLabel({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-2 block text-sm font-semibold text-slate-700">{label}</span>{children}</label>;
}

function PanelFooter({ close, submitLabel }: { close: () => void; submitLabel: string }) {
  return <div className="flex flex-col-reverse gap-3 border-t border-slate-200 bg-slate-50 p-4 sm:flex-row sm:p-6"><button className="min-h-11 flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-600 hover:bg-slate-100" onClick={close} type="button">Cancelar</button><button className="min-h-11 flex-1 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700" type="submit">{submitLabel}</button></div>;
}

function CategoryButton({ active, count, label, onClick }: { active: boolean; count: number; label: string; onClick: () => void }) {
  return <button className={`inline-flex min-h-11 items-center gap-2 rounded-xl border px-3.5 py-2 text-sm font-semibold transition ${active ? "border-blue-600 bg-blue-600 text-white" : "border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:text-blue-700"}`} onClick={onClick} type="button">{label}<span className={`rounded-full px-1.5 py-0.5 text-[10px] ${active ? "bg-white/20 text-white" : "bg-slate-100 text-slate-500"}`}>{count}</span></button>;
}

function DownloadIcon() {
  return <svg aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 3v12m0 0 4-4m-4 4-4-4M5 21h14" /></svg>;
}

function SearchIcon() {
  return <svg aria-hidden="true" className="absolute left-3 top-3 h-4 w-4 text-slate-400" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>;
}

function ExpenseColumnChart({ loading, periods }: { loading: boolean; periods: ExpensePeriod[] }) {
  const labels = { day: "Hoje", week: "Semana", month: "Mês" };
  return (
    <div className="mt-6">
      <div className="flex items-center justify-center gap-5 text-xs font-medium text-slate-500">
        <ChartLegend color="bg-amber-500" label="Combustível" />
        <ChartLegend color="bg-orange-500" label="Manutenção" />
        <ChartLegend color="bg-slate-400" label="Outros" />
      </div>
      <div className="relative mt-5 h-64 border-b border-slate-200">
        <div className="pointer-events-none absolute inset-0 grid grid-rows-4 divide-y divide-slate-100"><span /><span /><span /><span /></div>
        <div className="relative flex h-full items-end justify-around gap-5 px-4 sm:px-12">
          {(periods.length ? periods : (["day", "week", "month"] as const).map((period) => ({ period, total_cost: "0", fuel_percent: "0", maintenance_percent: "0", other_percent: "0" } as ExpensePeriod))).map((period) => {
            const total = Number(period.total_cost);
            const stacks = [
              { key: "other", percent: Number(period.other_percent), color: "bg-slate-400" },
              { key: "maintenance", percent: Number(period.maintenance_percent), color: "bg-orange-500" },
              { key: "fuel", percent: Number(period.fuel_percent), color: "bg-amber-500" },
            ];
            return (
              <div className="flex h-full w-24 flex-col items-center justify-end" key={period.period}>
                <strong className="mb-2 text-xs tabular-nums text-slate-700">{loading ? "—" : money.format(total)}</strong>
                <div className="flex h-44 w-14 flex-col-reverse justify-start overflow-hidden rounded-t-lg bg-slate-100 shadow-inner sm:w-16" title={`Total: ${money.format(total)}`}>
                  {total > 0 ? stacks.map((stack) => <div className={`grid place-items-center text-[10px] font-bold text-white transition-all ${stack.color}`} key={stack.key} style={{ height: `${stack.percent}%` }} title={`${stack.percent.toFixed(2)}%`}>{stack.percent >= 14 ? `${stack.percent.toFixed(0)}%` : ""}</div>) : <div className="grid h-full place-items-center text-xs text-slate-400">0%</div>}
                </div>
                <span className="mt-3 text-sm font-semibold text-slate-700">{labels[period.period]}</span>
              </div>
            );
          })}
        </div>
      </div>
      <p className="mt-3 text-center text-xs text-slate-400">Cada coluna representa 100% dos gastos registrados no período.</p>
    </div>
  );
}

function ChartLegend({ color, label }: { color: string; label: string }) {
  return <span className="flex items-center gap-1.5"><i className={`h-2.5 w-2.5 rounded-sm ${color}`} />{label}</span>;
}

function ExpenseLegend({ color, label, value }: { color: string; label: string; value: number }) {
  return <div className="flex items-center justify-between gap-4"><span className="flex items-center gap-2 text-slate-500"><i className={`h-2.5 w-2.5 rounded-full ${color}`} />{label}</span><strong className="tabular-nums text-slate-700">{money.format(value)}</strong></div>;
}

function UrgencyIcon({ urgent }: { urgent: boolean }) {
  return <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${urgent ? "bg-red-100 text-red-600" : "bg-amber-100 text-amber-600"}`}><svg aria-hidden="true" className="h-5 w-5" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24"><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.7 2.4 17.4A2 2 0 0 0 4.1 20h15.8a2 2 0 0 0 1.7-2.6L13.7 3.7a2 2 0 0 0-3.4 0Z"/></svg></span>;
}
