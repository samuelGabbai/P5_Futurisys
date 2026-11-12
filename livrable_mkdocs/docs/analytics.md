# Besoins analytiques et tableaux de bord

## Finalité et décisions attendues

Le besoin est de suivre l’utilisation et la fiabilité du service, puis d’aider le
référent RH à analyser des résultats agrégés. Les scores ne déclenchent aucune
mesure individuelle automatique. La qualité prédictive s’évalue séparément, sur
un jeu de données identifié avec de vraies cibles et un protocole documenté.

Le livrable définit les besoins et fournit deux vues SQL exploitables dans DBeaver,
Metabase ou un autre outil BI. Il ne suppose pas qu’une interface de dashboard soit
hébergée : le référentiel demande de **décrire les besoins analytiques**.

## Utilisateurs et accès

| Utilisateur | Besoin | Accès attendu |
| --- | --- | --- |
| Exploitant | Disponibilité, erreurs, latence et croissance du stockage | Agrégats techniques ; détail d’un incident sur habilitation |
| Data scientist | Versions, distribution des scores et métriques de validation | Agrégats par version et jeu de validation identifié |
| Référent RH habilité | Tendances collectives et compréhension des limites | Agrégats métier ; aucun dump des inputs ni liste de salariés par défaut |
| Responsable de livraison | Version et hash du modèle distribué | Métadonnées et droit `model:deliver`, distinct de l’utilisation des API |

Les comptes HTTP ne sont pas des comptes PostgreSQL. Le rôle SQL `hrnova_app` sert
au service, ses identifiants ne doivent pas être distribués aux utilisateurs BI.
Pour connecter un outil BI, l’administrateur crée un rôle dédié et lui donne
uniquement `SELECT` sur les vues nécessaires, sans accès direct aux tables RH.
Cette connexion et ses habilitations sont à provisionner selon le SI cible.

## Indicateurs et règles de calcul

| Tableau | Indicateurs | Source / définition | Actualisation |
| --- | --- | --- | --- |
| Activité | Nombre de requêtes et lignes traitées par jour et route | `analytics_daily_activity`, compte des échanges et somme de `row_count` | Lecture toutes les 5 minutes |
| Fiabilité | Succès, rejets, échecs, refus 401/403, requêtes incomplètes | Statuts de `api_exchanges` ; distinguer erreur utilisateur et incident serveur | Toutes les 5 minutes ; examiner les `pending` anciens |
| Temps de réponse | Moyenne et p95 par route ; latence complète du benchmark | `duration_ms` en base exclut la finalisation du log et le réseau ; le benchmark HTTP les inclut | Chaque jour et avant une livraison |
| Distribution des scores | Probabilité moyenne, proportion de requêtes au-dessus du seuil | `analytics_model_scores`, uniquement inférences unitaires réussies, par jour, hash et seuil | Quotidienne |
| Qualité prédictive | Rappel, précision, F1, ROC-AUC et calibration | Jeu labellisé dédié, date, protocole et version issus de la fiche modèle | À chaque validation du modèle, puis selon l’arrivée de labels |
| Stockage | Lignes par table, taille de base et croissance | Comptages et `pg_database_size` / `pg_total_relation_size` | Hebdomadaire, alerte sur tendance |

Filtres communs : période, route, statut, version du modèle et seuil de décision.
Ne pas mélanger les versions ou les règles de décision native et optimisée.
Les CSV de `/predict-proba/file` ont des sorties par ligne ; ils ne sont pas
implicitement inclus dans la vue des scores unitaires.

**Une requête n’est pas un salarié unique.** Des appels répétés ou des profils
synthétiques peuvent déplacer les distributions. La proportion de requêtes à risque
n’est ni le taux de turnover réel ni une estimation représentative de l’effectif.
Une analyse par département nécessite un lien salarié valide et une population
explicitement définie ; les JSON anonymes ne permettent pas cette jointure.

## Sources, qualité et confidentialité

Les vues sont créées par la migration
[`003_analytics_views.sql`](migrations/003_analytics_views.sql), exécutée par
`create_db.py` avec le rôle d’administration. Elles sont calculées à la lecture,
sans duplication des inputs et sans matérialisation à rafraîchir.

- La vue technique n’expose pas les inputs, les mots de passe ou les identifiants RH.
- La vue des scores ne publie un groupe qu’à partir de **5 requêtes**. Cette règle
  limite les petits groupes mais ne constitue pas une garantie d’anonymisation.
- Le dashboard métier doit isoler les appels de démonstration des usages réels.
  Les jeux de validation doivent porter une provenance explicite : un nom de fichier
  seul ne permet pas de certifier qu’une cible est réelle.
- Les statuts `pending` sont visibles et ne doivent pas être assimilés à des succès.
- Les contraintes source et les tests d’import contrôlent les identifiants, les
  valeurs absentes, les doublons et la conservation des données.

## Exemples de consultation

```sql
SELECT * FROM analytics_daily_activity
WHERE day >= CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY day DESC, route;

SELECT * FROM analytics_model_scores
WHERE day >= CURRENT_TIMESTAMP - INTERVAL '30 days'
ORDER BY day DESC, model_sha256;

SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size;
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

## Recette du besoin analytique

La vue technique doit correspondre aux échanges présents : les succès, rejets,
échecs et requêtes en cours totalisent le nombre de requêtes. La vue des scores
exclut les refus et les lots CSV, sépare les versions et masque les groupes de moins
de cinq requêtes. Les tests PostgreSQL vérifient ces propriétés sur des données
synthétiques ; aucune table de production n’est vidée pour la recette.

## Stockage et conservation

Le périmètre courant est un cas d’étude de 1 470 salariés, avec un historique qui
croît à chaque appel. Les exemples et benchmarks utilisent des données synthétiques.
Le stockage des inputs facilite l’audit mais duplique les valeurs à chaque requête.

Avant un usage sur données RH réelles, le responsable métier et le référent données
fixent la finalité, les personnes habilitées, la durée de conservation et les règles
d’archivage/purge. Aucun délai légal universel n’est supposé ici et aucune purge
automatique n’est activée. Une purge requiert le rôle d’administration, une sauvegarde
et le respect des clés étrangères ; le rôle applicatif ne peut pas supprimer les traces.

Pour dimensionner, mesurer la taille moyenne d’une requête tracée puis multiplier
par le nombre d’appels et la durée de conservation retenue. Séparer le volume du
dataset, les `model_inputs`, les outputs et les logs. Réévaluer les index et envisager
partitionnement/archivage si les mesures le justifient.
