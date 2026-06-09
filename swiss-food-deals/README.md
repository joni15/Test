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
| Coop, Denner, Lidl, Aldi | Extraction JSON-LD (schema.org) des pages d'actions |

⚠️ **Les scrapers web sont par nature fragiles** : les détaillants changent
régulièrement leurs sites et API, et certains rendent leur contenu uniquement
en JavaScript. Chaque scraper échoue silencieusement (liste vide) sans bloquer
les autres. Si **aucune** source ne répond (par ex. sans accès réseau),
l'application charge un jeu de données de démonstration clairement signalé
dans l'interface, afin de rester utilisable et testable hors ligne.

Pour ajouter une source : créer une classe dérivée de `BaseScraper` dans
`app/scrapers/` et l'enregistrer dans `ALL_SCRAPERS`
(`app/scrapers/__init__.py`).

## Avertissement

Les prix sont fournis à titre indicatif ; seuls les prix en magasin font foi.
Vérifiez les conditions d'utilisation des sites des détaillants avant tout
usage intensif ou commercial du scraping.
