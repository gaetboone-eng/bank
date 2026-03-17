# CGR Bank - PRD (Product Requirements Document)

## Problème Original
Application de gestion de flux bancaires locatifs "CGR Bank" avec:
- Connexion aux comptes bancaires via Enable Banking (Open Banking)
- Synchronisation avec une base Notion pour les locataires
- Matching automatique des transactions aux locataires
- Notifications pour les retards de paiement
- Authentification JWT
- Rapport mensuel des loyers payés/impayés
- Mécanisme "d'apprentissage" pour les associations manuelles
- Tableau de bord avec barres de progression globales et par structure
- Application PWA installable sur mobile
- Multi-utilisateurs: 3 associés partagent les données via une organisation commune
- Import automatique de toutes les banques depuis Enable Banking

## User Personas
- **Gaëtan** (gaet.boone@gmail.com) - Propriétaire principal
- **Romain** (romain.m@cgrbank.com) - Associé
- **Clément** (clement.h@cgrbank.com) - Associé

## Architecture

### Backend (FastAPI)
- **Auth**: JWT avec bcrypt
- **Base de données**: MongoDB (motor async)
- **Collections**: users, organizations, organization_members, banks, connected_banks, banking_auth_states, tenants, transactions, payments, notifications, user_settings
- **Intégrations**: Notion API, Enable Banking API
- **Scheduler**: APScheduler (sync auto 1er, 10ème, 20ème du mois)

### Frontend (React)
- **UI Components**: Shadcn/UI
- **Styling**: Tailwind CSS avec thème vert émeraude
- **State**: Context API pour auth
- **PWA**: Service worker + manifest.json

### Modèle Multi-Utilisateur
- Toutes les données partagées via `organization_id` (une seule organisation "CGR")
- Les utilisateurs voient les mêmes banques, locataires, transactions
- Le `user_id` est conservé pour traçabilité du créateur

## Ce qui a été implémenté

### MVP (Livré)
- ✅ Auth (register/login/logout) - JWT
- ✅ Dashboard avec stats temps réel (global + par structure)
- ✅ CRUD Banques (manuel + Enable Banking)
- ✅ CRUD Locataires avec sync Notion
- ✅ CRUD Transactions avec matching locataire
- ✅ Enregistrement paiements manuels
- ✅ Page Paramètres (Notion/Enable Banking)
- ✅ Interface responsive (mobile/desktop) - PWA installable
- ✅ Rapport mensuel avec logique 28 du mois précédent
- ✅ Barres de progression par structure dans le tableau de bord
- ✅ Bouton "Synchroniser" manuel
- ✅ Système multi-utilisateur avec organisation partagée
- ✅ Import automatique de toutes les banques Enable Banking
- ✅ Synchronisation auto login déclenchée

### Corrections (Février/Mars 2026)
- ✅ Erreur de syntaxe Python critique dans server.py (try sans except)
- ✅ Récursion infinie dans get_filter_for_user()
- ✅ Callback Enable Banking améliré (toujours redirige vers frontend)
- ✅ manual_sync() retourne maintenant correctement les résultats

## Endpoints API Clés
- POST /api/auth/login, /api/auth/register, GET /api/auth/me
- GET /api/dashboard/stats
- GET/POST /api/banks, PUT/DELETE /api/banks/{id}
- GET /api/banking/connected, POST /api/banking/connect/{aspsp}
- GET /api/banking/callback (OAuth callback)
- POST /api/banking/import-all (import auto depuis Enable Banking)
- GET/POST /api/tenants, POST /api/tenants/sync-notion
- GET/POST /api/transactions, POST /api/transactions/{id}/match/{tenant_id}
- GET /api/reports/structure-summary
- GET /api/payments/monthly-status
- POST /api/sync/manual (bouton Synchroniser du dashboard)
- POST /api/admin/migrate-to-org (création organisation)

## Backlog Priorisé

### P1 (Important - Prochaine session)
- [ ] **Telegram Notifications** - Intégration avec bot "OpenClaw" dans un groupe dédié CGR
  - Nécessite: Token bot Telegram (@BotFather) + ID groupe Telegram
  - Notifier: paiements reçus, retards, récapitulatif mensuel

### P2 (Nice to have)
- [ ] **Interface de matching manuel** - UI pour associer une transaction non reconnue à un locataire
  - Backend: /api/transactions/{tx_id}/match/{tenant_id} existe déjà
- [ ] **Notifications email** - Alternative/complément aux notifications Telegram

### P3 (Futur)
- [ ] **Refactoring server.py** - Le fichier fait +2200 lignes, diviser en modules (routes/, services/, models/)
- [ ] **Export PDF des rapports mensuels**
- [ ] **Graphiques de tendances** (Recharts)
- [ ] **Guide de déploiement** - Pour hébergement auto

## Comptes de Test
- gaet.boone@gmail.com / TenantLedger2024!
- romain.m@cgrbank.com / CGRbank2024!
- clement.h@cgrbank.com / CGRbank2024!

## Données Production (Mars 2026)
- 52 locataires dont 17 payés (35 impayés)
- 1 banque LCL (10,992.09€)
- 2 comptes LCL connectés via Open Banking
