# 🤖 Guide pour Claude - Continuation du projet CGR Bank

Bonjour Claude ! Voici un guide condensé pour reprendre ce projet.

## 📍 Où en sommes-nous ?

**Application fonctionnelle :** Tenant Finance Manager (gestionnaire de paiements de loyers)  
**URL :** https://tenant-finance-mgr.preview.emergentagent.com  
**Stack :** React + FastAPI + MongoDB

## ✅ Ce qui fonctionne déjà

✅ Authentification JWT  
✅ Dashboard avec stats en temps réel  
✅ Graphique historique (6 derniers mois) - **DERNIÈRE FONCTIONNALITÉ AJOUTÉE**  
✅ Synchronisation Notion (locataires)  
✅ Open Banking via Enable Banking  
✅ Matching automatique transactions → locataires  
✅ PWA fonctionnelle

## 🎯 Tâches prioritaires

### P1 : Notifications Telegram
**Fichier :** Créer `/app/backend/routes/notifications.py`  
**Objectif :** Envoyer alertes pour loyers impayés  
**Étapes :**
1. Demander token bot et chat_id à l'utilisateur
2. Implémenter envoi via Telegram Bot API
3. Ajouter configuration dans Settings
4. Tester avec comptes réels

### P2 : Interface de matching manuel
**Fichiers :** Créer `/app/frontend/src/pages/ManualMatching.jsx`  
**Backend déjà prêt :** `POST /api/transactions/{tx_id}/match/{tenant_id}`  
**Objectif :** UI pour associer manuellement transaction ↔ locataire

### P2 : URGENT - Refactorisation backend
**Problème :** `/app/backend/server.py` = 2500+ lignes  
**Solution :** Créer structure modulaire :
```
/app/backend/
├── routes/          # Endpoints organisés
├── services/        # Logique métier
├── models/          # Schémas Pydantic
└── server.py        # Point d'entrée
```

## 🚨 Règles critiques

1. ⚠️ **NE JAMAIS hardcoder** URLs/tokens → utiliser `.env`
2. ⚠️ **TOUJOURS exclure `_id`** dans MongoDB : `{"_id": 0}`
3. ⚠️ **Filtrer locataires résiliés** : `{"deactivated": {"$ne": True}}`
4. ⚠️ **Préfixer routes backend** par `/api`
5. ✅ Utiliser `datetime.now(timezone.utc)` (pas `utcnow()`)

## 🔑 Comptes de test

```
Email: gaet.boone@gmail.com
Password: TenantLedger2024!
(50 locataires, 27 payés)
```

## 📁 Fichiers importants

```
/app/backend/server.py           # ⚠️ MONOLITHE 2500 lignes
/app/frontend/src/pages/Dashboard.jsx
/app/frontend/src/components/HistoricalProgressChart.jsx  # 🆕
/app/backend/.env                # Secrets
/app/frontend/.env               # REACT_APP_BACKEND_URL
```

## 🔧 Commandes utiles

```bash
# Redémarrer services
sudo supervisorctl restart backend
sudo supervisorctl restart frontend

# Logs
tail -f /var/log/supervisor/backend.err.log

# MongoDB
mongosh mongodb://localhost:27017/tenant_ledger
```

## 📊 Endpoints API clés

```
POST /api/auth/login                         # Login
GET  /api/dashboard/stats                    # Stats principales
GET  /api/dashboard/monthly-history          # 🆕 Données graphique
GET  /api/tenants                            # Liste locataires
POST /api/transactions/auto-match            # Matching auto
POST /api/transactions/{tx_id}/match/{tenant_id}  # Matching manuel
POST /api/sync/manual                        # Sync complète
```

## 🐛 Problèmes connus

1. **Incohérence stats mineure** : 2 endpoints retournent 27 vs 28 payés (faible impact)
2. **Backend monolithique** : Nécessite refactorisation urgente

## 📖 Documentation complète

Tout est dans : `/app/PROJECT_SUMMARY.md` (15+ pages de détails)

## 💡 Conseils pour Claude

1. **Toujours lire PROJECT_SUMMARY.md en entier avant de commencer**
2. **Tester après chaque modification** (curl pour backend, screenshots pour frontend)
3. **Privilégier les petites modifications itératives**
4. **Demander confirmation avant grosses refactorisations**
5. **Utiliser search_replace pour éditer les fichiers existants**

## 🎨 Stack UI

- Tailwind CSS
- Shadcn UI (composants dans `/app/frontend/src/components/ui/`)
- Recharts pour graphiques
- Lucide React pour icônes

## 🔄 Workflow type

```
1. Lire la tâche dans PROJECT_SUMMARY.md
2. Planifier l'implémentation
3. Modifier/créer fichiers nécessaires
4. Tester backend avec curl
5. Tester frontend avec screenshot
6. Documenter changements
7. Demander validation utilisateur
```

## 📞 En cas de problème

1. Vérifier les logs : `tail -f /var/log/supervisor/backend.err.log`
2. Vérifier services : `sudo supervisorctl status`
3. Tester l'auth : `curl -X POST ... /api/auth/login`
4. Consulter PROJECT_SUMMARY.md section "Troubleshooting"

## 🎯 Objectif à atteindre

Application de gestion locative 100% automatisée avec :
- ✅ Dashboard temps réel
- ✅ Matching intelligent
- ⏳ Notifications automatiques
- ⏳ Rapports PDF
- ⏳ Architecture modulaire

---

**Prêt à coder ? Commence par lire PROJECT_SUMMARY.md ! 🚀**

*PS : L'utilisateur préfère communiquer en français 🇫🇷*
