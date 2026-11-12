# Modèle, données et performances

## Objectif et données

Le modèle estime la probabilité de la classe `a_quitte_l_entreprise = Oui` pour
le cas d'étude RH TechNova Partners. L'encodage est `Non = 0`, `Oui = 1`.
Il fournit une aide à l'analyse ; les associations statistiques observées ne sont
pas des causes de départ établies.

Les trois CSV de `Data/` comportent chacun 1 470 lignes. La jointure rapproche
`sirh.id_employee`, `sondage.code_sondage` et le nombre extrait de `eval.eval_number`.
Le dataset fusionné compte 31 colonnes avant feature engineering, cible comprise.
La cible contient 1 233 salariés restés et 237 partis, soit environ 16,12 % de départs.
Les sources, clés et règles d'import sont documentées dans [PostgreSQL](database.md).

## Préparation des variables

Le notebook conserve les noms source, y compris leurs particularités orthographiques.
Les pourcentages comme `11 %` deviennent `11.0` ; les variables binaires et la
fréquence de déplacement sont encodées. Les colonnes nominales `domaine_etude`,
`departement` et `poste` utilisent `OneHotEncoder(drop="first", handle_unknown="ignore")`.
La cible et les identifiants ne sont pas des variables explicatives.

Le feature engineering ajoute des indicateurs de rémunération relative et la
moyenne des quatre dimensions de satisfaction. Le ratio revenu/âge, l'indicateur
`fortement_sous_paye`, les quatre satisfactions élémentaires et le groupe d'ancienneté
intermédiaire sont exclus de la matrice finale. Celle-ci comporte **43 variables
numériques**, décrites dans [le contrat d'entrée](features.md).

L'artefact n'embarque pas l'encodeur ni les références de médianes comme une pipeline
de préparation réutilisable. L'API accepte donc des variables déjà préparées : elle
ne transforme pas un CSV RH brut en features. Le notebook reste la référence de préparation.

## Entraînement et choix du modèle

La séparation est stratifiée, avec `test_size=0.20` et `random_state=42` :

- entraînement : 1 176 salariés, dont 190 départs ;
- test : 294 salariés, dont 47 départs.

La validation croisée utilise cinq folds stratifiés, mélangés avec la même graine.
La régression logistique emploie un `StandardScaler` dans une pipeline, ajusté dans
chaque fold. La forêt n'utilise pas de scaling.

Les résultats suivants sont ceux **enregistrés dans le notebook**, pas un nouveau
benchmark exécuté lors de la rédaction. Les cellules sont numérotées à partir de zéro.

| Comparaison sur le train | F1 moyen ± écart-type | ROC-AUC moyenne |
| --- | --- | --- |
| Dummy stratifié, cellule 31 | 0,1644 ± 0,0300 | 0,5054 |
| Régression logistique équilibrée, cellule 31 | 0,4968 ± 0,0280 | 0,8279 |
| Random Forest initial, cellule 31 | 0,4189 ± 0,0967 | 0,8024 |
| Random Forest optimisé, cellule 34 | 0,5048 ± 0,0714 | Non reportée pour cette grille |
| LightGBM, cellule 54 | 0,5226 ± 0,0426 | 0,8030 |
| Random Forest + SMOTE, cellule 55 | 0,4600 ± 0,0936 | 0,7689 |

La forêt retenue permet une modélisation non linéaire, sans scaling, avec pondération
des classes et limitation de la profondeur. La régression logistique et LightGBM
restent des alternatives compétitives : ces résultats ne prouvent pas une supériorité
générale du modèle publié. Le notebook n'effectue pas une comparaison finale sur le
test de tous les concurrents avec des seuils optimisés de manière identique.

La grille teste 16 combinaisons sur cinq folds, soit 80 ajustements :
`n_estimators ∈ {200, 300}`, `max_depth ∈ {5, 10}`, `min_samples_split ∈ {2, 5}`,
`min_samples_leaf ∈ {1, 2}`, avec F1 comme critère de sélection.
Les paramètres retenus, confirmés dans l'artefact local, sont :

| Paramètre | Valeur |
| --- | --- |
| Estimateur | `RandomForestClassifier` |
| `n_estimators` | 300 |
| `max_depth` | 5 |
| `min_samples_split` | 5 |
| `min_samples_leaf` | 2 |
| `class_weight` | `balanced` |
| `random_state` | 42 |
| Calibration | `CalibratedClassifierCV(method="sigmoid", cv=5)` |

## Calibration et décision

Les probabilités calibrées out-of-fold du train servent à choisir le seuil
maximisant le F1 sur la courbe précision-rappel. Le seuil de l'artefact courant
est **0,22318137541604238**, contre un seuil natif proche de 0,50 pour la décision
par classe la plus probable.

Sur les prédictions OOF ayant servi à choisir ce seuil (cellules 36 et 39),
le F1 passe de 0,3788 à 0,5180 et le rappel de 0,2632 à 0,5684.
Ces valeurs servent à la sélection du seuil et ne constituent pas une évaluation
indépendante de ce choix.

Les routes `/predict` et `/employees/{employee_id}/score` utilisent le seuil
optimisé. `/predict/file` utilise `model.predict`, donc la règle native du modèle.
`/score/file` expose les deux conventions : `score` natif et métriques `threshold_*`.

## Performances sur le test

Source : sortie de la **cellule 41** du notebook, sur 294 lignes. Les nombres sont
arrondis à quatre décimales et concernent la classe positive pour précision/rappel/F1.

| Métrique | Seuil 0,50 | Seuil optimisé |
| --- | --- | --- |
| Accuracy | 0,8163 | 0,8027 |
| Précision | 0,3478 | 0,4203 |
| Rappel | 0,1702 | 0,6170 |
| F1 | 0,2286 | 0,5000 |
| ROC-AUC | 0,7692 | 0,7692 |
| Brier score | 0,1226 | 0,1226 |
| Log loss | 0,3890 | 0,3890 |

Le seuil optimisé détecte davantage de départs, au prix de davantage d'alertes.
Une accuracy élevée seule serait trompeuse sur cette cible : prédire toujours
« resté » donnerait déjà 247/294, soit environ 0,8401, sur ce test.
ROC-AUC, Brier et log loss mesurent les probabilités et ne changent pas lorsqu'on
modifie uniquement le seuil de décision.

Le [relevé de performances](model_metrics.json) associe ces résultats au hash du
notebook et de l'artefact examinés le **27 octobre 2026**. Ces résultats historiques
doivent être remplacés et revalidés après un nouvel entraînement.

## Interprétabilité et limites

Le notebook propose importance native, importance par permutation et SHAP, dont
des explications locales. Les calculs SHAP portent sur les forêts et leurs contributions ;
ils ne constituent pas nécessairement une décomposition exacte de la probabilité
après calibration. Ils ne démontrent pas un lien causal.

Plusieurs limites doivent accompagner l'usage du modèle :

- Médianes de rémunération et encodeur nominal sont ajustés **avant le split** dans
  le notebook actuel. Même sans utiliser directement la cible, cela introduit de
  l'information du test dans la préparation et peut influencer les performances.
- La sélection d'hyperparamètres et du seuil réutilise le train ; une validation
  imbriquée ou un jeu de validation dédié renforcerait l'estimation.
- Le test ne contient que 47 départs ; les métriques n'ont pas d'intervalles de
  confiance fournis dans le notebook et aucune validation temporelle/externe n'est disponible.
- L'âge, le genre, le statut marital et des proxys RH peuvent créer des disparités.
  Une analyse des erreurs par sous-population est à réaliser avant usage opérationnel.
- La version actuelle valide des types et formats, pas toutes les bornes métier
  possibles ni la stabilité des distributions en production.

L'amélioration prioritaire est une pipeline de préparation sérialisable, ajustée
uniquement sur les folds d'entraînement. Le [protocole de maintenance](maintenance.md)
décrit les vérifications requises avant toute nouvelle publication.
