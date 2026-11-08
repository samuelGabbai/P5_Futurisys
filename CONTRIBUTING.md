# Contribuer à HRNova

## Organisation du dépôt

- Modules à la racine : routes, contrats, authentification, inférence, BDD et export du modèle.
- `scripts/` : initialisation, vérification, mesure et déploiement.
- `tests/` : tests unitaires, fonctionnels et intégration PostgreSQL.
- `deployment/` et `.github/workflows/` : environnements et CI/CD.
- `docs/` : guides MkDocs et preuves de validation publiables.
- `Data/`, `artifacts/`, `examples/` : données d’étude, modèle de confiance et exemples synthétiques.
- `.local/`, `reports/`, `htmlcov/`, `site/`, `build/` : sorties locales, ignorées par Git.

Les secrets restent dans `.env`, `.local/` ou les secrets GitHub. Ne pas committer
de mots de passe, de fichiers `.pyc`, de répertoires `__pycache__`, de métadonnées
`*.egg-info` ou de rapports temporaires. Les exports `docs/openapi.json` et
`docs/database_validation.json` sont volontairement versionnés comme livrables.

## Branches et commits

Utiliser `feat/sujet`, `fix/sujet`, `docs/sujet` ou `test/sujet` pour une modification.
`development` prépare le développement, `develop` la préproduction et `main` la production.
Le job de tests fournit un environnement de test isolé.

Format des prochains commits : `type(périmètre): action précise`, par exemple
`fix(auth): authentifier les appels de validation PostgreSQL` ou
`test(deploy): vérifier la construction et les rôles dans le conteneur`.
Expliquer dans le corps le problème, le changement et les vérifications utiles.
L’historique existant n’est pas réécrit.

## Avant une pull request

```bash
uv sync --locked --extra api --extra dev --extra docs
uv run --no-sync pytest
uv run --no-sync python scripts/export_openapi.py
uv run --no-sync mkdocs build --strict
uv build
```

Pour la validation complète, définir `TEST_DATABASE_URL` vers une base PostgreSQL
dédiée. Les tests créent et détruisent des schémas isolés ; certains vérifient aussi
la création d’une base temporaire avec un rôle de test autorisé. Ne pas leur donner
les identifiants de la base de production.

La CI construit aussi l’image Docker et teste ses routes et permissions avec
PostgreSQL. Protéger `main` et exiger le contrôle « Validation avant fusion » dans
GitHub ; cette protection doit être activée dans les réglages du dépôt.
