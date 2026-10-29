# HRNova : comprendre, utiliser et maintenir le projet

HRNova estime le risque de départ d'un salarié à partir de variables RH préparées.
Le dépôt associe un notebook d'analyse et d'entraînement, une API FastAPI, PostgreSQL
pour la traçabilité et une pipeline de validation et publication du modèle.

## Choisir son parcours

| Objectif | Point d'entrée |
| --- | --- |
| Installer et lancer le projet | [Installation](installation.md) |
| Envoyer un fichier et récupérer une prédiction | [Référence API et exemples](api.md) |
| Comprendre les variables attendues | [Contrat des variables](features.md) |
| Consulter les performances et leurs limites | [Documentation du modèle](model.md) |
| Comprendre les composants et leurs échanges | [Architecture](architecture.md) |
| Consulter les entrées, sorties et erreurs | [PostgreSQL](database.md) et [logs API](api_logs.md) |
| Mettre à jour ou revenir à une version précédente | [Maintenance](maintenance.md) |
| Comprendre GitHub Actions et Hugging Face | [Déploiement](deployment.md) |

## Ce qui est disponible

- 1 470 salariés issus de trois sources, reliées par identifiant.
- Un Random Forest calibré, utilisant 43 variables et un seuil de décision optimisé.
- Sept endpoints métier ou techniques, avec validation Pydantic et documentation OpenAPI.
- Enregistrement des inputs et outputs du modèle en PostgreSQL, reliés par un `X-Request-ID`.
- Tests automatiques, construction du package et export vers `SamGabb/hrnova` sur Hugging Face.

L'usage documenté est local. La publication sur le Hub stocke le modèle ; elle ne
constitue pas le déploiement d'une API ni l'hébergement de PostgreSQL.
Les performances consignées dans [la fiche modèle](model.md) proviennent des sorties
du notebook présentes dans le dépôt, et ne constituent pas une mesure continue en production.

## Lire la documentation

Les fichiers Markdown sont lisibles directement dans GitHub. Pour une navigation
avec recherche et schémas rendus :

```bash
uv sync --locked --extra docs
uv run --no-sync mkdocs serve
```

Ouvrir <http://127.0.0.1:8001>. Ce port est distinct du port `8000` de l'API.
La documentation Swagger de l'API lancée est disponible à
<http://127.0.0.1:8000/docs>, ReDoc à <http://127.0.0.1:8000/redoc> et le contrat
machine à <http://127.0.0.1:8000/openapi.json>.
