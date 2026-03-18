import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TrendingUp, Loader2, Shield, BarChart2, Bell } from "lucide-react";
import { toast } from "sonner";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Connexion réussie");
      navigate("/");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Identifiants incorrects");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Panneau gauche – branding */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 bg-slate-900 p-12 relative overflow-hidden">
        {/* Cercles décoratifs */}
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />

        {/* Logo */}
        <div className="flex items-center gap-3 relative z-10">
          <div className="w-10 h-10 rounded-xl bg-emerald-500 flex items-center justify-center shadow-lg">
            <TrendingUp className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-white" style={{ fontFamily: "Manrope" }}>CGR Bank</span>
        </div>

        {/* Hero */}
        <div className="relative z-10 space-y-8">
          <div>
            <h2 className="text-4xl font-bold text-white leading-tight mb-4" style={{ fontFamily: "Manrope" }}>
              Gérez vos SCIs<br />
              <span className="text-emerald-400">simplement.</span>
            </h2>
            <p className="text-slate-400 text-lg">
              Suivi des loyers, virements bancaires et structures immobilières en temps réel.
            </p>
          </div>

          <div className="space-y-4">
            {[
              { icon: BarChart2, text: "Vue d'ensemble par structure (SCI)" },
              { icon: Shield, text: "Connexion bancaire sécurisée Open Banking" },
              { icon: Bell, text: "Alertes retards de paiement" },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-4 h-4 text-emerald-400" />
                </div>
                <span className="text-slate-300 text-sm">{text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <p className="text-slate-600 text-xs relative z-10">
          © 2026 CGR Bank · Gestion locative privée
        </p>
      </div>

      {/* Panneau droit – formulaire */}
      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-slate-50">
        {/* Logo mobile uniquement */}
        <div className="lg:hidden flex items-center gap-3 mb-10">
          <div className="w-10 h-10 rounded-xl bg-emerald-900 flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-slate-900" style={{ fontFamily: "Manrope" }}>CGR Bank</span>
        </div>

        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-slate-900 mb-1" style={{ fontFamily: "Manrope" }}>
              Connexion
            </h1>
            <p className="text-slate-500 text-sm">Entrez vos identifiants pour continuer</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-slate-700 font-medium text-sm">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="vous@exemple.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="h-11 border-slate-200 focus:border-emerald-500 focus:ring-emerald-500/20 bg-white"
                data-testid="login-email-input"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-slate-700 font-medium text-sm">Mot de passe</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="h-11 border-slate-200 focus:border-emerald-500 focus:ring-emerald-500/20 bg-white"
                data-testid="login-password-input"
              />
            </div>

            <Button
              type="submit"
              className="w-full h-11 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg shadow-sm shadow-emerald-500/20 transition-all"
              disabled={loading}
              data-testid="login-submit-btn"
            >
              {loading ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Connexion...</>
              ) : "Se connecter →"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Pas de compte ?{" "}
            <Link to="/register" className="text-emerald-600 hover:text-emerald-700 font-medium" data-testid="register-link">
              Créer un accès
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
