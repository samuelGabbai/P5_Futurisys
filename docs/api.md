# Référence API et exemples d'utilisation

## Accès et contrat

URL locale : `http://127.0.0.1:8000`. Suivre [l'installation](installation.md) avant
les exemples : PostgreSQL et l'artefact complet doivent être disponibles.

| Interface | Adresse |
| --- | --- |
| Swagger UI, pour envoyer des requêtes | <http://127.0.0.1:8000/docs> |
| ReDoc, pour lire le contrat | <http://127.0.0.1:8000/redoc> |
| Contrat OpenAPI JSON | <http://127.0.0.1:8000/openapi.json> |

Le [contrat OpenAPI exporté](openapi.json) est également téléchargeable depuis cette
documentation. Il est généré par `python scripts/export_openapi.py` sans connexion BDD
et peut être importé dans un client compatible OpenAPI. La version servie par l'API
lancée reste la référence pour le processus en cours.

La version déclarée de l'API est `1.0.0`. L'API locale n'a pas d'authentification HTTP
et n'active pas de CORS spécifique. Elle est lancée par défaut sur l'interface locale.
Chaque réponse inclut `X-Request-ID` pour retrouver l'échange dans la BDD.
Le journal d'accès étant stocké en PostgreSQL, les pages de documentation nécessitent
elles aussi une connexion BDD fonctionnelle.

## Endpoints

| Méthode et chemin | Entrée | Résultat |
| --- | --- | --- |
| `GET /health` | Aucune | Disponibilité BDD/journal et chargement du modèle |
| `GET /features` | Aucune | Noms des variables attendues |
| `POST /predict` | JSON `features` | Probabilité de départ et décision au seuil optimisé |
| `POST /predict/file` | CSV, champ multipart `file` | Classes natives, une par ligne |
| `POST /predict-proba/file` | Même CSV | Probabilités par classe, une ligne par entrée |
| `POST /score/file` | CSV avec cible réelle | Accuracy native et métriques au seuil optimisé |
| `GET /employees/{employee_id}/score` | ID entier positif | Score d'un salarié dont les variables sont en BDD |

Les cinq routes d'inférence utilisent obligatoirement le circuit
[API → BDD → modèle → BDD → réponse](architecture.md). `/health` ne garantit pas à
lui seul que tous les salariés et toutes les métadonnées de modèle ont été importés ;
utiliser le script de vérification pour un contrôle fonctionnel complet.

## Santé et variables

```bash
curl -i http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/features
```

La réponse de santé est `{"status":"ok"}`. `/features` renvoie un objet
`{"features":[...]}` : la version actuelle utilise les 43 noms du [contrat des variables](features.md).

## Prédiction JSON

Un exemple complet et **synthétique**, sans salarié réel, est fourni dans
[`examples/predict.json`](https://github.com/samuelGabbai/P5_Futurisys/blob/main/examples/predict.json).
Ses valeurs dérivées illustrent le contrat technique ; elles ne constituent pas
une validation métier de ce profil.

```bash
curl -i -X POST http://127.0.0.1:8000/predict \
  -H 'Content-Type: application/json' \
  --data-binary @examples/predict.json
```

Structure de réponse illustrative, valeurs numériques non garanties pour ce profil :

```json
{
  "probability": 0.3,
  "threshold": 0.22318137541604238,
  "prediction": 1,
  "decision": "Risque de départ élevé"
}
```

`probability` est la probabilité de la classe positive `1`. `prediction` vaut `1`
si cette probabilité atteint le seuil optimisé, et `0` sinon pour le modèle courant.
Les champs supplémentaires en dehors de `features` sont refusés.

## Prédiction et probabilités par CSV

Le CSV doit être UTF-8, avec en-tête, au moins une ligne et au plus **10 Mio de contenu
du fichier**. Toutes les variables doivent être préparées et encodées. Ne pas envoyer
les trois CSV RH bruts, la cible ou une colonne d'ID à ces deux routes.
La limite est contrôlée à la lecture du fichier ; ce n'est pas une limite de taille
globale appliquée au transfert HTTP multipart par un proxy.

```bash
curl -i -X POST http://127.0.0.1:8000/predict/file \
  -F 'file=@examples/employees.csv'

curl -i -X POST http://127.0.0.1:8000/predict-proba/file \
  -F 'file=@examples/employees.csv'
```

Les exemples CSV fournis sont synthétiques. Les réponses ont respectivement la forme :

```json
{"row_count":2,"predictions":[0,1]}
```

```json
{"row_count":2,"classes":[0,1],"probabilities":[[0.8,0.2],[0.4,0.6]]}
```

Ces valeurs sont illustratives. L'ordre des résultats suit celui des lignes ; les
colonnes de `probabilities` suivent le tableau `classes`. `/predict/file` appelle
la décision native `model.predict` : son résultat peut différer de `/predict`, qui
utilise le seuil optimisé.

Paramètre commun : `separator`, `,` par défaut, ou `;` :

```bash
curl -X POST 'http://127.0.0.1:8000/predict/file?separator=%3B' \
  -F 'file=@mon_fichier_separe_par_points_virgules.csv'
```

## Évaluer un fichier avec ses vraies réponses

```bash
curl -i -X POST http://127.0.0.1:8000/score/file \
  -F 'file=@examples/employees_with_target.csv'
```

La colonne cible par défaut est `a_quitte_l_entreprise` avec `0/1` ou `Non/Oui`.
Le fichier d'exemple contient des réponses fictives : son score démontre le
fonctionnement de l'endpoint, pas la performance réelle du modèle.
Pour un autre nom : `?target_column=depart_reel`. Les options peuvent être combinées
avec `&separator=%3B`.

| Champ de réponse | Signification |
| --- | --- |
| `row_count` | Nombre de lignes évaluées |
| `score`, `metric` | Accuracy de `model.score`, donc de la décision native ; `metric = accuracy` |
| `threshold` | Seuil optimisé de l'artefact |
| `threshold_accuracy` | Proportion de décisions correctes avec ce seuil |
| `threshold_precision` | Proportion de vrais départs parmi les alertes |
| `threshold_recall` | Proportion de départs détectés |
| `threshold_f1` | Moyenne harmonique précision/rappel |

Sans vraie réponse, le score supervisé ne peut pas être calculé. Un score obtenu sur
des données d'entraînement ou des étiquettes fictives ne mesure pas la généralisation.

## Score par identifiant

```bash
curl -i http://127.0.0.1:8000/employees/1/score
```

La réponse reprend les champs de `/predict`, plus `employee_id`. Les variables
proviennent de `prepared_employees` pour le hash exact du modèle chargé.
Cette route ne cherche pas les features dans le dictionnaire embarqué dans le joblib.

## Exemple Python

```python
import json
from pathlib import Path
import httpx

with httpx.Client(base_url="http://127.0.0.1:8000", timeout=60) as client:
    payload = json.loads(Path("examples/predict.json").read_text(encoding="utf-8"))
    response = client.post("/predict", json=payload)
    response.raise_for_status()
    print(response.headers["X-Request-ID"], response.json())
    with Path("examples/employees.csv").open("rb") as file:
        response = client.post("/predict-proba/file", files={"file": ("employees.csv", file, "text/csv")})
    response.raise_for_status()
    print(response.json())
```

## Erreurs et diagnostic

| Code | Cause habituelle |
| --- | --- |
| `404` | Salarié absent de la BDD ou route inconnue |
| `405` | Mauvaise méthode HTTP |
| `413` | Contenu du fichier supérieur à 10 Mio |
| `422` | JSON/CSV invalide, colonnes manquantes ou supplémentaires, cible ou ID invalide |
| `500` | Erreur de calcul, artefact invalide ou sortie ne respectant pas le contrat |
| `503` | BDD indisponible, sortie non persistable, modèle absent ou version non importée |

Une erreur de colonnes contient `detail.missing_features` et `detail.unexpected_features`.
Une erreur de valeurs contient des éléments `loc`, `msg`, `type`, sans copie des
valeurs brutes refusées. Les détails et l'étape atteinte se consultent via
[les logs API](api_logs.md), à partir du `X-Request-ID`.
La [validation Pydantic](api_validation.md) décrit les contraintes exactes et leurs tests.

Swagger et ReDoc sont générés par FastAPI à partir du même contrat que les routes :
[documentation officielle](https://fastapi.tiangolo.com/features/).
