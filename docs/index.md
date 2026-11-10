<div class="hero">
<h1>HRNova, du modèle à l’API</h1>
<p>Un modèle de prédiction RH accessible par FastAPI, avec PostgreSQL pour tracer chaque échange et GitHub Actions pour vérifier les changements.</p>
<p><a class="md-button md-button--primary" href="demarrage/">Démarrer le projet</a> <a class="md-button" href="https://github.com/samuelGabbai/P5_Futurisys">Voir le dépôt GitHub</a></p>
</div>

## Choisir un guide

<div class="guide-grid">
<a class="guide-card" href="demarrage/"><strong>01 · Démarrer</strong><span>Cloner le dépôt, installer, lancer PostgreSQL et l’API.</span></a>
<a class="guide-card" href="api/"><strong>02 · Utiliser l’API</strong><span>Swagger, authentification et appels JSON ou CSV.</span></a>
<a class="guide-card" href="model/"><strong>03 · Comprendre le modèle</strong><span>Données, métriques et limites de la prédiction.</span></a>
<a class="guide-card" href="database/"><strong>04 · Explorer la base</strong><span>Schéma PostgreSQL, import et traçabilité.</span></a>
<a class="guide-card" href="deployment/"><strong>05 · Déployer</strong><span>Environnements, CI/CD et cible de livraison.</span></a>
<a class="guide-card" href="ressources/"><strong>06 · Aller plus loin</strong><span>Sécurité, tests, performances et maintenance.</span></a>
</div>

## Repères rapides

- **1 470 salariés** dans les trois sources RH ; **43 variables** préparées pour le modèle.
- **9 endpoints** FastAPI, documentés dans Swagger à `http://127.0.0.1:8000/docs`.
- **263 tests réussis et 100 % des lignes couvertes** lors de la recette PostgreSQL du 10 novembre 2026 ([périmètre et limites](validation.md)).

L’application est démontrée **en local**. Le dépôt Model Hugging Face est une cible de publication distincte de l’API. Les [résultats prédictifs](model.md) proviennent du notebook enregistré et ne sont pas une mesure en production.
