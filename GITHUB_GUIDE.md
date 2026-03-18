# 📤 Guide pour pousser vers GitHub

## 🚀 Étapes rapides

### 1. Initialiser Git (si pas déjà fait)
```bash
cd /app
git init
git branch -M main
```

### 2. Ajouter tous les fichiers
```bash
git add .
```

### 3. Créer le premier commit
```bash
git commit -m "🎉 Initial commit - CGR Bank Tenant Finance Manager

✨ Fonctionnalités:
- Dashboard interactif avec stats en temps réel
- Graphique historique d'évolution des paiements
- Intégration Notion pour sync locataires
- Intégration Enable Banking (Open Banking)
- Matching automatique intelligent transactions ↔ locataires
- Support multi-utilisateurs avec organisations
- PWA avec service worker
- Gestion locataires résiliés

📚 Documentation complète incluse:
- PROJECT_SUMMARY.md (guide développeur 600+ lignes)
- README.md (présentation projet)
- CLAUDE_HANDOFF.md (guide rapide pour Claude)

🔧 Stack: React + FastAPI + MongoDB
"
```

### 4. Créer un nouveau repository sur GitHub

1. Aller sur https://github.com/new
2. Nom suggéré : `cgr-bank-tenant-manager`
3. Description : `🏦 Assistant bancaire intelligent pour gestion automatisée des paiements de loyers`
4. **Choisir :** Private (recommandé pour clés API)
5. **NE PAS** initialiser avec README (on a déjà le nôtre)
6. Cliquer "Create repository"

### 5. Lier le repository local à GitHub

```bash
# Remplacer YOUR_USERNAME par votre nom d'utilisateur GitHub
git remote add origin https://github.com/YOUR_USERNAME/cgr-bank-tenant-manager.git

# Vérifier
git remote -v
```

### 6. Pousser le code

```bash
git push -u origin main
```

Si demande d'authentification :
- **Username :** Votre nom d'utilisateur GitHub
- **Password :** Utiliser un **Personal Access Token** (pas votre mot de passe)

### 7. Créer un Personal Access Token (si nécessaire)

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token (classic)
3. Nom : "CGR Bank Deploy"
4. Cocher : `repo` (tous)
5. Generate token
6. **COPIER LE TOKEN** (vous ne le reverrez plus)
7. Utiliser ce token comme mot de passe

---

## ⚠️ IMPORTANT : Sécurité

### Fichiers sensibles exclus automatiquement

Le `.gitignore` exclut déjà :
- ✅ `*.env` (variables d'environnement)
- ✅ `*.pem` (clés privées)
- ✅ `*credentials.json*`
- ✅ `*token.json*`
- ✅ `__pycache__/`, `node_modules/`

### Vérifier avant de pousser

```bash
# Vérifier qu'aucun secret n'est inclus
git status

# Si vous voyez des fichiers .env ou .pem, NE PAS les ajouter !
```

### Si vous avez accidentellement ajouté des secrets

```bash
# Retirer un fichier du staging
git reset HEAD fichier-sensible.env

# Ou annuler le dernier commit (si pas encore pushé)
git reset --soft HEAD~1
```

---

## 📝 Commits futurs - Convention suggérée

```bash
# Nouvelle fonctionnalité
git commit -m "✨ feat: Ajout notifications Telegram"

# Correction de bug
git commit -m "🐛 fix: Correction matching locataires"

# Refactorisation
git commit -m "♻️ refactor: Séparation server.py en modules"

# Documentation
git commit -m "📝 docs: Mise à jour README"

# Tests
git commit -m "✅ test: Ajout tests pour API auth"

# Performance
git commit -m "⚡️ perf: Optimisation requêtes MongoDB"
```

---

## 🔄 Workflow quotidien

```bash
# 1. Récupérer les dernières modifications
git pull origin main

# 2. Faire vos modifications
# ... coder ...

# 3. Voir ce qui a changé
git status
git diff

# 4. Ajouter les fichiers modifiés
git add fichier1.js fichier2.py
# Ou tout ajouter :
git add .

# 5. Commit avec message descriptif
git commit -m "✨ feat: Description de votre feature"

# 6. Pousser vers GitHub
git push origin main
```

---

## 🌿 Branches (optionnel mais recommandé)

Pour travailler sur de nouvelles fonctionnalités sans casser la version stable :

```bash
# Créer une branche pour Telegram
git checkout -b feature/telegram-notifications

# Travailler sur la feature
# ... coder ...
git add .
git commit -m "✨ feat: Telegram notifications"

# Pousser la branche
git push origin feature/telegram-notifications

# Sur GitHub, créer une Pull Request
# Merger dans main quand prêt
```

---

## 📦 Créer une release

Quand vous atteignez un milestone important :

```bash
# Créer un tag
git tag -a v1.0.0 -m "🎉 Release 1.0.0 - Dashboard et graphique historique"

# Pousser le tag
git push origin v1.0.0
```

Sur GitHub :
1. Aller dans "Releases"
2. "Draft a new release"
3. Choisir le tag `v1.0.0`
4. Titre : "Version 1.0.0 - Dashboard complet"
5. Description : Liste des features
6. Publish release

---

## 🤝 Collaborer avec d'autres

### Ajouter un collaborateur

1. GitHub → Settings → Collaborators
2. Add people
3. Entrer email ou username

### Cloner pour un nouveau développeur

```bash
git clone https://github.com/YOUR_USERNAME/cgr-bank-tenant-manager.git
cd cgr-bank-tenant-manager

# Backend setup
cd backend
pip install -r requirements.txt
cp .env.example .env  # Éditer avec les vraies clés

# Frontend setup
cd ../frontend
yarn install
cp .env.example .env

# Lancer
# Terminal 1:
cd backend && uvicorn server:app --reload

# Terminal 2:
cd frontend && yarn start
```

---

## 🔍 Commandes utiles

```bash
# Voir l'historique des commits
git log --oneline --graph --all

# Voir les différences avant de commit
git diff

# Annuler les modifications locales d'un fichier
git checkout -- fichier.js

# Voir les branches
git branch -a

# Supprimer une branche locale
git branch -d nom-branche

# Changer de branche
git checkout main
```

---

## 📞 Aide

En cas de problème :
- [Documentation Git](https://git-scm.com/doc)
- [GitHub Guides](https://guides.github.com)
- [Oh Shit, Git!?!](https://ohshitgit.com) - Solutions aux problèmes courants

---

## ✅ Checklist finale

Avant de pousser :
- [ ] `.gitignore` en place
- [ ] Pas de fichiers `.env` ou `.pem` dans git status
- [ ] README.md à jour
- [ ] Code testé et fonctionnel
- [ ] Message de commit descriptif
- [ ] Branche correcte (main ou feature)

---

**Prêt à pousser ! 🚀**

Pour toute question : gaet.boone@gmail.com
