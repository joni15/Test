# 🇨🇭 Bonnes Affaires CH

Agrégateur quotidien des meilleures offres alimentaires en Suisse. L'application
interroge chaque jour les promotions des grands détaillants (Migros, Coop,
Denner, Lidl, Aldi), les déduplique, les classe par rabais et les expose via
une API REST et une interface web.

## Démarrage rapide

```bash
cd swiss-food-deals
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Puis ouvrir <http://localhost:8000>. La documentation interactive de l'API est
disponible sur <http://localhost:8000/docs>.

## Fonctionnement

1. **Agrégation** — au démarrage (si la base est vide) puis chaque jour à
   06h00 (Europe/Zurich), tous les scrapers sont lancés en parallèle
   (`app/aggregator.py`). Les offres sont dédupliquées et stockées en SQLite
   (`deals.db`).
2. **API** (`app/main.py`) :
   - `GET /api/deals` — liste filtrable : `?retailer=`, `?category=`,
     `?search=`, `?min_discount=`, `?sort=discount|price|retailer`
   - `GET /api/stats` — détaillants, catégories, date du dernier refresh
   - `POST /api/refresh` — force une nouvelle agrégation
3. **Interface web** (`app/static/`) — recherche, filtres par détaillant /
   catégorie / rabais minimum, tri, bouton d'actualisation.

## Sources de données

| Détaillant | Méthode |
|---|---|
| Migros | API de recherche produits (jeton invité) |
| Coop, Denner, Lidl, Aldi | Extraction JSON-LD (schema.org) des pages d'actions, avec repli navigateur headless (Playwright) |

Ordre de repli de l'agrégation : **scrapers en direct → flux distant publié
par GitHub Actions → données de démonstration** (clairement signalées dans
l'interface).

## Accéder aux offres réelles

Les sites des détaillants utilisent des protections anti-bot et du rendu
JavaScript ; de plus, certains environnements (dont les sandboxes Claude Code
sur le web) bloquent ces domaines au niveau réseau. Trois chemins, du plus
simple au plus direct :

### 1. Workflow GitHub Actions (recommandé)

Les runners GitHub ont un accès internet complet. Le workflow
`.github/workflows/aggregate-deals.yml` :

1. installe Playwright + Chromium ;
2. lance `python -m app.cli aggregate --output data/deals.json` ;
3. committe le flux `data/deals.json` dans le dépôt — il refuse de publier
   si seules les données de démonstration sont disponibles.

L'application le consomme automatiquement via `raw.githubusercontent.com`
(accessible même depuis les sandboxes) quand les scrapers directs échouent.
URL du flux configurable via `DEALS_FEED_URL`. Déclenchement : quotidien à
06h15 (cron, uniquement sur la branche par défaut) ou manuel via l'onglet
*Actions* → *Run workflow*.

### 2. Exécution locale avec Playwright

```bash
pip install playwright && python -m playwright install chromium
uvicorn app.main:app
```

Quand une requête HTTP simple est refusée ou renvoie une page sans données,
les scrapers rechargent automatiquement la page dans Chromium headless,
ce qui passe le rendu JavaScript et la plupart des protections anti-bot.

### 3. Débloquer le réseau de l'environnement Claude Code

Dans [claude.ai/code](https://claude.ai/code) → réglages de l'environnement →
accès réseau, autoriser : `www.migros.ch`, `www.coop.ch`, `www.denner.ch`,
`www.lidl.ch`, `www.aldi-suisse.ch` (voir la
[documentation](https://code.claude.com/docs/en/claude-code-on-the-web)).

### Diagnostic

```bash
python -m app.cli doctor
```

Indique, pour chaque source, si elle est bloquée par la politique réseau de
l'environnement, par une protection anti-bot, ou si la page ne contient pas
de données exploitables sans JavaScript.

⚠️ **Les scrapers web restent par nature fragiles** : les détaillants
changent régulièrement leurs sites et API. Chaque scraper échoue
silencieusement (liste vide) sans bloquer les autres.

Pour ajouter une source : créer une classe dérivée de `BaseScraper` dans
`app/scrapers/` et l'enregistrer dans `ALL_SCRAPERS`
(`app/scrapers/__init__.py`).

## Avertissement

Les prix sont fournis à titre indicatif ; seuls les prix en magasin font foi.
Vérifiez les conditions d'utilisation des sites des détaillants avant tout
usage intensif ou commercial du scraping.
