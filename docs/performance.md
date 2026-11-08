# Performances et gestion des volumes

## Protocole reproductible

Le benchmark contacte une API réellement lancée en HTTP, avec HTTP Basic à chaque
appel, le modèle du projet et PostgreSQL pour les entrées/sorties et la traçabilité.
Il mesure le temps complet côté client, et non uniquement `model.predict_proba`.
Chaque scénario comporte un préchauffage exclu puis 8 requêtes mesurées.

```bash
uv run --no-sync python scripts/benchmark_api.py \
  --requests 8 --concurrency 1,4 --batch-sizes 100,1000
```

Le compte de vérification est lu depuis `HRNOVA_VERIFY_USERNAME` /
`HRNOVA_VERIFY_PASSWORD`, ou `.local/api-credentials.env` généré par
`scripts/manage_users.py --bootstrap-local`. Aucun identifiant n’est envoyé en
argument de commande ni enregistré dans le rapport.

La commande crée des échanges tracés avec des profils synthétiques répétés issus
de `examples/predict.json`. Elle ne mesure pas la performance prédictive. Pour un
usage courant, lancer le benchmark hors des heures d’utilisation et conserver son
rapport avec les caractéristiques de la machine et la version du service.

## Résultats mesurés

Le [rapport JSON complet](performance_results.json) contient la date UTC, la machine,
les percentiles, les codes HTTP et les débits. Mesure sur macOS ARM64, 10 CPU,
Python 3.13.9, PostgreSQL local et un processus Uvicorn.

| Route / lignes par requête | Concurrence | p95 HTTP | Débit requêtes/s | Débit lignes/s | Erreurs |
| --- | --- | --- | --- | --- | --- |
| JSON / 1 | 1 | 264,60 ms | 3,983 | 3,983 | 0/8 |
| CSV / 100 | 1 | 300,81 ms | 3,565 | 356,485 | 0/8 |
| CSV / 1 000 | 1 | 509,70 ms | 2,159 | 2 159,369 | 0/8 |
| JSON / 1 | 4 | 468,66 ms | 8,571 | 8,571 | 0/8 |
| CSV / 100 | 4 | 535,47 ms | 7,660 | 766,005 | 0/8 |
| CSV / 1 000 | 4 | 1 146,07 ms | 3,592 | 3 592,498 | 0/8 |

**48 requêtes mesurées, aucune erreur**, plus six préchauffages. La concurrence
améliore le débit mais augmente la latence. Le coût du hachage de mot de passe et
les transactions d’audit sont inclus. Le modèle est mis en cache par processus.

Ces petits échantillons caractérisent cette machine et ces entrées ; ils ne prouvent
ni un débit maximal, ni un SLA en production, ni une tenue sous une charge prolongée.
Le p95 sur huit requêtes reste une estimation peu précise. Répéter avec davantage
de requêtes et une distribution de profils représentative avant tout dimensionnement.

## Budgets de recette

Pour la démonstration locale, les objectifs indicatifs sont zéro erreur et un p95
inférieur à 2 secondes pour les six scénarios ci-dessus. Ils sont satisfaits par
cette mesure. Le seuil peut être rendu bloquant :

```bash
uv run --no-sync python scripts/benchmark_api.py --max-p95-ms 2000
```

Il n’est pas imposé sur un runner partagé GitHub : sa variabilité rendrait ce test
instable. La CI impose en revanche une vraie prédiction HTTP, les permissions et
la disponibilité du conteneur avec PostgreSQL. Un environnement de performance
stable pourra ajouter un budget bloquant sur la machine cible.

## Limites de requête et mémoire

- CSV UTF-8 : **10 Mio**, **10 000 lignes de données** et garde de **128 colonnes**.
- Le contrat métier reste exactement les 43 variables du modèle, plus la cible pour
  `/score/file` ; la garde de 128 colonnes n’autorise pas de colonnes supplémentaires.
- Le parseur s’arrête dès la première ligne dépassant la limite, avant conversion
  en DataFrame et avant inférence. La limite porte sur les lignes non vides.
- Une taille ou un nombre de lignes excessif produit 413 ; des colonnes excessives
  ou un contrat invalide produisent 422. Les rejets restent tracés sans calcul modèle.
- Les fichiers sont lus dans une enveloppe mémoire bornée par la limite d’octets,
  mais le décodage, la validation et les DataFrames ajoutent des allocations. La
  consommation maximale n’a pas été profilée : une mesure mémoire reste nécessaire
  avant augmentation des limites.
- Découper les volumes supérieurs en plusieurs fichiers ; chaque lot a son propre
  `X-Request-ID`. La version actuelle n’est pas un moteur de traitement massif asynchrone.

La JSON unitaire reste une requête de profil ; ne pas l’utiliser pour transférer
un dataset. Pour une exposition distante, configurer également les limites HTTP,
les délais et la limitation des tentatives au niveau du proxy HTTPS.

## PostgreSQL et croissance

SQLAlchemy utilise un pool avec vérification des connexions. Les index couvrent
les dates, routes, statuts et liens de requêtes. Les inputs/outputs sont persistés
et relus avant réponse ; ce coût est volontaire et fait partie du benchmark.

Le dataset comporte 1 470 salariés ; les traces augmentent à chaque appel et chaque
ligne de CSV crée une entrée. Les vues analytiques permettent le suivi quotidien.
La [documentation analytique](analytics.md) précise les besoins, les mesures de
stockage, l’accès BI et le processus de conservation à définir avec le métier.
