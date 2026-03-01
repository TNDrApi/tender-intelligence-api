# ✅ Checklist Victor — Actions Requises

*Ce que tu dois faire toi-même (nécessite une identité humaine ou un accès navigateur)*
*Temps estimé total : ~45 minutes*

---

## ÉTAPE 1 — Créer un compte GitHub (5 min)

> Nécessaire pour héberger le code et déployer sur Railway/Render.

1. Va sur **https://github.com/signup**
2. Crée un compte avec ton email (`adolvictor@gmail.com` ou autre)
3. Valide l'email de confirmation
4. Crée un **nouveau dépôt public** :
   - Nom : `tender-intelligence-api`
   - Visibility : **Public**
   - Cocher "Add a README" : **Non** (le projet en a déjà un)
   - Cliquer **Create repository**
5. Note l'URL du repo (ex: `https://github.com/TONPSEUDO/tender-intelligence-api`)

---

## ÉTAPE 2 — Uploader le code sur GitHub (5 min)

Sur la page du repo vide, GitHub affiche des instructions. Utilise la méthode **"Upload files"** :

1. Clique sur **"uploading an existing file"** (lien sur la page du repo vide)
2. Glisse-dépose le dossier `tender-api/` depuis ton ordinateur
3. Ou utilise le bouton "choose your files" et sélectionne tous les fichiers du dossier
4. Message de commit : `Initial commit: Tender Intelligence API v1.0`
5. Cliquer **Commit changes**

**Fichiers à uploader (tous dans le dossier `tender-api/`) :**
```
main.py
requirements.txt
Procfile
railway.json
render.yaml
.env.example
README.md
models/__init__.py
models/notice.py
routers/__init__.py
routers/search.py
routers/sectors.py
routers/notices.py
services/__init__.py
services/boamp.py
services/ted.py
```

---

## ÉTAPE 3 — Déployer sur Railway (10 min)

> Railway est la meilleure option : déploiement automatique, SSL gratuit, URL stable.

1. Va sur **https://railway.app**
2. Cliquer **"Start a New Project"**
3. Choisir **"Deploy from GitHub repo"**
4. Autoriser Railway à accéder à GitHub (bouton OAuth)
5. Sélectionner le repo `tender-intelligence-api`
6. Railway détecte automatiquement Python et lance le build
7. Attendre ~2 minutes que le déploiement se termine (barre verte)
8. Cliquer sur **"Settings"** → **"Generate Domain"**
9. Note l'URL publique (ex: `https://tender-intelligence-api-production.up.railway.app`)

**Test de vérification :**
```
Ouvre dans ton navigateur :
https://TON-URL.railway.app/health
```
Tu dois voir : `{"status": "ok", "version": "1.0.0", ...}`

```
https://TON-URL.railway.app/docs
```
Tu dois voir l'interface Swagger interactive.

---

## ÉTAPE 4 — Créer un compte RapidAPI Provider (10 min)

1. Va sur **https://rapidapi.com/auth/sign-up**
2. Crée un compte (utilise `adolvictor@gmail.com`)
3. Valide l'email
4. Va sur **https://rapidapi.com/provider** (onglet "My APIs")
5. Cliquer **"Add New API"**
6. Remplir :
   - **API Name** : `Tender Intelligence API`
   - **Short Description** : *(copie depuis `RAPIDAPI_PRODUCT.md` — section "Tagline")*
   - **Category** : Business Software → Government & Legal
7. Cliquer **"Add API"**

---

## ÉTAPE 5 — Configurer l'API sur RapidAPI (15 min)

### Onglet "Configuration"
1. **Base URL** : colle l'URL Railway de l'étape 3
   → Ex: `https://tender-intelligence-api-production.up.railway.app`
2. **Protocol** : HTTPS
3. **Authentication** : RapidAPI Key (géré automatiquement par RapidAPI)
4. Cliquer **Save**

### Onglet "Endpoints"
RapidAPI peut importer automatiquement depuis ton OpenAPI/Swagger.

1. Cliquer **"Import from URL"**
2. Entrer : `https://TON-URL.railway.app/openapi.json`
3. RapidAPI importe tous les endpoints automatiquement ✅

### Onglet "Pricing" (Monetize)
Configurer 4 plans (copie exactement) :

| Plan Name | Price | Requests/month | Rate limit |
|-----------|-------|----------------|------------|
| FREE | $0 | 100 | 10/min |
| BASIC | $29 | 1000 | 30/min |
| PRO | $99 | 10000 | 60/min |
| ENTERPRISE | $299 | Unlimited | 200/min |

Pour chaque plan :
1. Cliquer **"Add Plan"**
2. Remplir Name, Price, Quota
3. Cliquer **Save**

### Onglet "Hub Listing"
1. **Long Description** : colle le contenu de `RAPIDAPI_PRODUCT.md` (section "Long Description")
2. **Tags** : `Public Procurement, Government, France, Europe, BOAMP, TED, Tenders, B2B`
3. **Thumbnail** : utilise une image libre de droit (suggestion : icône d'immeuble gouvernemental)
4. Cliquer **Publish to Hub**

---

## ÉTAPE 6 — Vérification finale (5 min)

1. **Test depuis RapidAPI** :
   - Va dans l'onglet "Test" de ton API sur RapidAPI
   - Appelle `GET /search?q=informatique&source=boamp`
   - Vérifie que tu reçois des résultats JSON ✅

2. **Partage l'URL de ta page RapidAPI** :
   - Format : `https://rapidapi.com/TONPSEUDO/api/tender-intelligence-api`
   - C'est ton URL de vente

3. **Surveille les métriques** :
   - Dashboard RapidAPI → "Analytics" → vois les appels entrants

---

## Résumé des comptes à créer

| Service | URL | Utilisation | Coût |
|---------|-----|-------------|------|
| GitHub | github.com/signup | Hébergement code | Gratuit |
| Railway | railway.app | Déploiement serveur | Gratuit (500h/mois) |
| RapidAPI | rapidapi.com | Marketplace API | Gratuit (commission 20%) |

**Commission RapidAPI** : 20% sur chaque vente.
→ Sur 99€/mois × 5 clients = 495€ brut → **~396€ net** (après commission)
→ Pour atteindre 500€ net : il faut **~7 clients** à 99€

---

## En cas de problème

| Problème | Solution |
|----------|---------|
| Railway build échoue | Vérifie que tous les fichiers sont uploadés sur GitHub, notamment `requirements.txt` |
| `/health` retourne "boamp: unreachable" | Normal si Railway bloque les IPs — contacte Railway support ou utilise Render |
| RapidAPI n'importe pas les endpoints | Importe manuellement depuis `/openapi.json` ou entre les endpoints un par un |
| Erreur 502 sur `/search` | L'API BOAMP peut être temporairement down — teste à nouveau dans 10 min |
