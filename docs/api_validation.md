# Validation Pydantic et tests des endpoints

Les contrats d'entrée et de sortie sont définis dans [`schemas.py`](https://github.com/samuelGabbai/P5_Futurisys/blob/main/schemas.py).
FastAPI expose ces schémas dans `/docs` et `/openapi.json`.

## Données entrantes

`POST /predict` reçoit un objet JSON de la forme :

```json
{
  "features": {
    "nom_variable_1": 2.5,
    "nom_variable_2": 4
  }
}
```

Les noms sont illustratifs : fournir exactement toutes les variables de `GET /features`.
Le modèle Pydantic `PredictionRequest` interdit les champs supplémentaires en dehors
de `features`, impose un dictionnaire non vide et valide chaque valeur numérique.
Les entiers, décimaux et chaînes numériques (par exemple `"2.5"`) sont normalisés
en flottants. Les booléens, `null`, listes, objets, texte non numérique, NaN et infinis
sont refusés avec un code **422**.

La liste des variables attendues est fournie au validateur Pydantic par le contexte
du modèle chargé. Les colonnes manquantes ou supplémentaires sont signalées avec
`missing_features` et `unexpected_features`. L'ordre des colonnes est libre ; elles
sont réordonnées avant l'enregistrement et l'inférence.

Pour les trois routes CSV, chaque ligne passe par la même validation Pydantic,
via `BatchPredictionRequest`. Les erreurs indiquent la ligne (indice à partir de zéro
dans `rows`) et la variable concernée. Les valeurs brutes refusées ne sont pas
recopiées dans la réponse d'erreur ou dans les logs de validation. Au plus vingt
erreurs de valeurs sont détaillées par réponse.

`POST /score/file` impose en plus des vraies réponses : `ScoreTargets` n'accepte
que `0`, `1`, `Non` ou `Oui` (casse et espaces externes normalisés). Le nom de la
colonne cible doit être non vide et ne peut pas désigner une variable explicative.
Le séparateur CSV doit être une virgule ou un point-virgule.

L'identifiant de `GET /employees/{employee_id}/score` doit être un entier entre
1 et 2 147 483 647, compatible avec la clé PostgreSQL. Un identifiant mal formé
produit **422** ; un salarié absent de la BDD produit **404**.

## Sorties du modèle

Toutes les réponses possèdent un schéma Pydantic. Le service d'inférence valide les
résultats **avant leur insertion dans `model_outputs`** :

- classes binaires entières `0` ou `1`, sans conversion silencieuse d'une valeur comme `0.5` ;
- probabilités, seuil et métriques finis et compris entre `0` et `1` ;
- une prédiction ou une ligne de probabilités par entrée ;
- deux probabilités par ligne, dans l'ordre des classes, dont la somme vaut `1`
  avec une tolérance absolue de `0.000001` ;
- classes `0` et `1` distinctes ;
- métrique du score natif fixée à `accuracy`.

Une sortie invalide produit **500** : les inputs restent tracés, la requête est
marquée `failed` et la sortie invalide n'est ni renvoyée au client ni enregistrée
comme un résultat valide. Les problèmes d'accès PostgreSQL produisent **503**.

Ces contrôles garantissent la conformité des données et des résultats au contrat
de l'API. La pertinence métier et les performances prédictives doivent être évaluées
sur un jeu de validation indépendant ; Pydantic ne les mesure pas.

## Tests individuels

| Endpoint | Vérifications |
| --- | --- |
| `GET /health` | Réponse valide et modèle indisponible |
| `GET /features` | Liste des variables et modèle indisponible |
| `POST /predict` | Prédiction, seuil, variables absentes, valeurs invalides, normalisation des nombres |
| `POST /predict/file` | Plusieurs lignes, ordre des colonnes, fichiers invalides, prédictions incorrectes du modèle |
| `POST /predict-proba/file` | Ordre des classes, séparateur, valeurs invalides, bornes et forme de la matrice, somme des probabilités |
| `POST /score/file` | Vraies réponses requises, encodage Non/Oui, métriques, cible invalide et score hors bornes |
| `GET /employees/{employee_id}/score` | Lecture depuis la BDD, salarié absent, ID nul, négatif, non numérique ou trop grand |

Les tests se trouvent dans [`tests/test_api.py`](https://github.com/samuelGabbai/P5_Futurisys/blob/main/tests/test_api.py),
[`tests/test_api_validation.py`](https://github.com/samuelGabbai/P5_Futurisys/blob/main/tests/test_api_validation.py) et les tests
de traçabilité existants. Ils utilisent un modèle simulé pour vérifier les réponses
attendues de chaque route sans dépendre d'un nouvel entraînement.

```bash
uv sync --locked --extra api --extra dev
uv run --no-sync pytest tests/test_api.py tests/test_api_validation.py
# Suite complète utilisée en CI :
uv run --no-sync pytest --cov-report=xml --junitxml=reports/junit.xml
```

Le workflow GitHub Actions exécute ces tests à chaque push et pull request, avec
PostgreSQL et un schéma isolé par test. Les entrées refusées sont rejetées avant
tout appel modèle ; les tests vérifient également l'absence de sortie enregistrée.

Références : [validateurs Pydantic et contexte](https://docs.pydantic.dev/latest/concepts/validators/)
et [types contraints Pydantic](https://docs.pydantic.dev/latest/api/types/).
