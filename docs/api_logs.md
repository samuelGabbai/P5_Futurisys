# Consulter les logs API dans DBeaver

Les échanges sont enregistrés dans `public.api_exchanges`. La vue `public.api_logs`
présente les mêmes informations avec des intitulés français, sans recopier les données.
Dans DBeaver, actualiser la connexion puis ouvrir **Schemas → public → Views → api_logs**.

```sql
SELECT date_requete, requete_id, methode, route, statut, code_http, duree_ms,
       message, etape, lignes, variables, fichier
FROM api_logs
ORDER BY date_requete DESC
LIMIT 50;
```

Une prédiction réussie indique par exemple :
`predict terminé : 2 ligne(s), 43 variable(s) ; entrées et sorties enregistrées.`
Un fichier incomplet précise les colonnes manquantes et inattendues. Le champ
`detail_erreur` contient aussi le détail structuré, utilisable dans une requête SQL.

```sql
-- Erreurs avec leur cause, leur fichier et l'étape atteinte.
SELECT date_requete, requete_id, route, code_http, message, etape, fichier,
       type_erreur, detail_erreur
FROM api_logs
WHERE code_http >= 400
ORDER BY date_requete DESC;

-- Contexte et résumé du résultat pour un X-Request-ID donné.
SELECT * FROM api_logs WHERE requete_id = 'UUID_RENVOYE_PAR_API';
```

Les nouveaux champs comprennent :

| Champ | Contenu |
| --- | --- |
| `message` | Résumé lisible du succès ou de l'erreur |
| `duree_ms` | Temps jusqu'à la préparation de la réponse, hors écriture finale du log et transfert réseau |
| `etape` | Dernière étape persistée : `received`, `inputs_saved`, `model_running`, `outputs_saved`, `completed` |
| `lignes`, `variables` | Dimensions des entrées validées et enregistrées pour le modèle |
| `contexte` | Adresse du client, route générique, ID salarié éventuel, séparateur, colonne cible, fichier, taille et dimensions du CSV lu |
| `detail_erreur` | Colonnes manquantes, champs invalides ou type et message de l'exception ; SQLSTATE pour les erreurs PostgreSQL disponibles |
| `resume_resultat` | Score et métriques, prédiction unitaire ou nombre de prédictions par classe ; les sorties complètes restent dans `model_outputs` |

Si un fichier est refusé avant enregistrement des entrées, `lignes` et `variables`
restent vides ; les dimensions du fichier déjà lu figurent dans `contexte`.
Une erreur conserve l'étape atteinte pour distinguer validation, calcul et stockage.
Les erreurs PostgreSQL n'enregistrent ni SQL ni paramètres liés. Les en-têtes
d'authentification, le corps JSON brut, les valeurs rejetées par Pydantic et les
paramètres de requête autres que `separator` et `target_column` ne sont pas recopiés
dans ces logs. Les URL avec mot de passe sont masquées dans les messages d'exception.
Les entrées métier validées restent dans la table dédiée `model_inputs`.

La migration [`002_explicit_api_logs.sql`](migrations/002_explicit_api_logs.sql) est
additive et réexécutable ; `create_db.py` l'applique automatiquement avec le rôle
d'administration. Les anciennes traces conservent leurs données et n'inventent pas
de détails absents (`etape = legacy` pour les lignes antérieures à la migration).
Redémarrer l'API après mise à jour pour utiliser les nouveaux champs.
