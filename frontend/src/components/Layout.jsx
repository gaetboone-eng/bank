import { Outlet, NavLink, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import {
  LayoutDashboard,
  Users,
  Building2,
  ArrowLeftRight,
  Settings,
  LogOut,
  CalendarDays,
  TrendingUp
} from "lucide-react";
import { Button } from "@/components/ui/button";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Tableau de bord" },
  { to: "/monthly-report", icon: CalendarDays, label: "Rapport mensuel" },
  { to: "/tenants", icon: Users, label: "Locataires" },
  { to: "/banks", icon: Building2, label: "Banques" },
  { to: "/transactions", icon: ArrowLeftRight, label: "Transactions" },
  { to: "/settings", icon: Settings, label: "Paramètres" },
];

const bottomNavItems = [
  { to: "/", icon: LayoutDashboard, label: "Accueil" },
  { to: "/tenants", icon: Users, label: "Locataires" },
  { to: "/banks", icon: Building2, label: "Banques" },
  { to: "/transactions", icon: ArrowLeftRight, label: "Flux" },
  { to: "/settings", icon: Settings, label: "Réglages" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* ── Sidebar desktop ── */}
      <aside className="hidden lg:flex flex-col w-64 bg-slate-900 min-h-screen fixed inset-y-0 left-0 z-50">
        {/* Logo */}
        <div className="px-6 py-6 border-b border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500 flex items-center justify-center shadow-lg">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-white tracking-tight text-lg" style={{ fontFamily: "Manrope" }}>
                CGR Bank
              </h1>
              <p className="text-xs text-slate-400">Gestion de SCIs</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                isActive
                  ? "flex items-center gap-3 px-4 py-2.5 rounded-lg bg-emerald-500/20 text-emerald-400 font-medium border-l-2 border-emerald-400 text-sm"
                  : "flex items-center gap-3 px-4 py-2.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors text-sm"
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div className="px-3 py-4 border-t border-slate-700/50">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-slate-800 mb-2">
            <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
              <span className="text-white text-sm font-bold">
                {user?.name?.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-white text-sm truncate">{user?.name}</p>
              <p className="text-xs text-slate-400 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors text-sm"
          >
            <LogOut className="w-4 h-4" />
            Déconnexion
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="flex-1 flex flex-col min-w-0 lg:ml-64">
        {/* Header mobile */}
        <header className="lg:hidden bg-slate-900 px-4 py-3 flex items-center justify-between sticky top-0 z-40 shadow-md">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500 flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-white" style={{ fontFamily: "Manrope" }}>CGR Bank</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center">
            <span className="text-white text-sm font-bold">
              {user?.name?.charAt(0).toUpperCase()}
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-8 overflow-auto pb-24 lg:pb-8">
          <Outlet />
        </main>
      </div>

      {/* ── Bottom navigation mobile ── */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-700/50 z-50 shadow-2xl">
        <div className="flex items-center justify-around px-2 py-1">
          {bottomNavItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex flex-col items-center gap-0.5 px-3 py-2 rounded-xl transition-colors min-w-0 flex-1 ${
                  isActive ? "text-emerald-400" : "text-slate-500"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <div className={`p-1.5 rounded-lg transition-colors ${isActive ? "bg-emerald-500/20" : ""}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-medium truncate">{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
