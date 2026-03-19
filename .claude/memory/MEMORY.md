# Projet CGR Bank - Tenant Finance Manager

## Contexte
Application de gestion automatisée des paiements de loyers pour SCIs propriétaires de locaux médicaux.
- GitHub: https://github.com/gaetboone-eng/bank
- Stack: React 18 + FastAPI + MongoDB
- Ancienne URL de prod: https://tenant-finance-mgr.preview.emergentagent.com (emergent.sh)
- Langue: Français

## État du projet (Mars 2026)
Fonctionnel sur emergent.sh. Code cloné localement dans le dossier cloné.

### Fonctionnel
- Auth JWT, dashboard stats, graphique historique 6 mois
- Sync Notion (locataires), Enable Banking (Open Banking)
- Matching auto transactions → locataires, PWA

### À faire (priorités)
- P1: Notifications Telegram (bot "OpenClaw")
- P2: UI matching manuel (backend déjà prêt)
- ✅ Refactorisation server.py — FAIT (backend/routes/, services/, core/)

## Structure fichiers clés
- backend/server.py — point d'entrée (refactorisé)
- backend/routes/ — auth, banks, tenants, transactions, payments, dashboard, banking, sync
- backend/services/ — matching, enable_banking
- backend/core/ — config, database, auth
- frontend/src/pages/Dashboard.jsx
- frontend/src/components/HistoricalProgressChart.jsx
- frontend/src/lib/api.js

## Règles critiques
1. NE JAMAIS hardcoder URLs/tokens → .env
2. TOUJOURS {"_id": 0} dans les projections MongoDB
3. Filtrer locataires résiliés: {"deactivated": {"$ne": True}}
4. Préfixer routes backend par /api
5. Utiliser datetime.now(timezone.utc) pas utcnow()

## Comptes de test
- gaet.boone@gmail.com / TenantLedger2024! (50 locataires, 27 payés)
- romain.m@cgrbank.com / CGRbank2024!
- clement.h@cgrbank.com / CGRbank2024!

## Préférences utilisateur
- Communication en français
- Confirmer avant grosses refactorisations
