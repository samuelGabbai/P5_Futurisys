# HRNova — Notes pour la soutenance

20 diapositives : 18 principales et 2 annexes. Les notes sont aussi intégrées au PowerPoint.

## 01 — Du modèle à une API traçable

Présenter le projet comme un parcours complet : partir de trois sources RH, estimer une probabilité de départ puis rendre le calcul utilisable et vérifiable. Le périmètre actuel est un service local, avec publication du modèle sur le Hub. Les performances viennent du notebook enregistré et les tests logiciels vérifient le fonctionnement du service.

Source : État du projet examiné le 27 octobre 2026

## 02 — Un outil d'aide à l'analyse RH

L'objectif est de mieux comprendre et repérer les situations associées aux départs. La cible connue est binaire : salarié resté ou parti. Le résultat est une probabilité et une décision selon un seuil. Souligner que le modèle ne prouve pas les causes de départ et ne remplace pas une analyse métier. Il faut relier les fausses alertes et les départs manqués à des coûts et à des actions définies avec les RH.

Source : Sources : README.md ; docs/model.md

## 03 — Trois sources, une population de 1 470 salariés

Les trois fichiers ont chacun 1 470 lignes, mais concernent la même population : on ne dispose pas de 4 410 salariés différents. Les clés sont rapprochées entre les sources, tout en conservant leur représentation d'origine en base. La classe positive représente 237 départs sur 1 470, soit environ 16,1 %. Le déséquilibre justifie de regarder précision, rappel et F1, pas uniquement l'accuracy.

Source : Sources : Data/*.csv ; docs/model.md ; docs/database.md

## 04 — Transformer les données en 43 variables numériques

La préparation est exécutée dans le notebook. Elle fusionne les sources, convertit les pourcentages, encode les variables et crée notamment des indicateurs de rémunération relative et une satisfaction moyenne. La cible et les identifiants sont exclus des variables explicatives. L'API reçoit le résultat de cette préparation ; elle ne fait pas la transformation d'un fichier RH brut. Certaines références sont aujourd'hui calculées avant le split : cette limite sera détaillée plus loin.

Source : Sources : notebook, cellules 12 à 28 ; docs/features.md

## 05 — Séparer l'évaluation du choix du seuil

La séparation stratifiée réserve 20 % des données pour le test : 294 salariés dont 47 départs. Le train compte 1 176 salariés dont 190 départs. Les modèles sont comparés par validation croisée à cinq folds ; la grille optimise le F1 et la calibration utilise sigmoid avec cinq folds. Le seuil est choisi sur les probabilités out-of-fold du train. Les transformations apprises avant le split limitent toutefois l'indépendance globale de l'évaluation actuelle.

Source : Sources : notebook, cellules 28 à 41 ; docs/model.md

## 06 — Comparer plusieurs approches, sans surinterpréter le classement

Cette comparaison utilise les F1 moyens en validation croisée enregistrés dans le notebook. LightGBM atteint ici le meilleur F1 moyen, tandis que la régression logistique est également compétitive. La forêt optimisée est le modèle exporté, mais il ne faut pas affirmer sa supériorité générale. Les écarts-types et les protocoles de choix des hyperparamètres doivent être pris en compte. Aucune comparaison finale sur le test de tous les concurrents avec des seuils optimisés identiquement n'est fournie.

Source : Sources : notebook, cellules 31, 34, 54 et 55 ; docs/model.md

## 07 — Le modèle livré : forêt régularisée et probabilités calibrées

La grille explore 16 combinaisons, évaluées sur cinq folds. Le modèle retenu utilise 300 arbres avec une profondeur maximale de cinq, un minimum de cinq observations pour une séparation et deux par feuille. La pondération des classes est balanced. La calibration sigmoid est réalisée avec CalibratedClassifierCV, cv=5. Le fichier complet conserve aussi le seuil, les noms de variables, la classe positive et les variables préparées des salariés pour l'import local.

Source : Sources : artefact local ; docs/model.md ; notebook, cellules 34 et 36

## 08 — Le seuil optimisé augmente le rappel sur le test

Sur les 294 salariés du test, le rappel passe de 17,0 % à 61,7 % lorsque le seuil passe de 0,50 à environ 0,2232. Le F1 augmente de 0,229 à 0,500. La précision reste de 42,0 % : toutes les alertes ne sont pas de vrais départs. L'accuracy au seuil optimisé est de 80,27 % et la ROC-AUC de 0,7692. Une stratégie qui prédit toujours resté atteindrait déjà 84,0 % d'accuracy sur ce test : l'accuracy seule ne suffit pas. Les valeurs viennent du notebook, sans réévaluation pendant la fabrication du support.

Source : Source : notebook, cellule 41 ; docs/model_metrics.json • test : 294 lignes, 47 départs

## 09 — Chaque inférence suit un circuit contrôlé

Le client fournit du JSON, un CSV préparé ou un identifiant salarié. FastAPI et Pydantic valident le contrat. Le service enregistre les inputs en PostgreSQL, les relit dans une nouvelle session, puis appelle le modèle. Les outputs sont validés, committés et relus avant la réponse HTTP. Toutes les routes d'inférence passent par ce service. Ce choix ajoute des accès BDD mais garantit que les valeurs effectivement calculées sont celles stockées.

Source : Sources : api.py ; schemas.py ; inference.py ; docs/architecture.md

## 10 — PostgreSQL structure les données et l'historique

La BDD contient huit tables. Les sources sont employees, surveys et evaluations, reliées par identifiant salarié. prepared_employees conserve les variables par salarié et version de modèle. model_versions conserve le SHA-256, les noms de variables et le seuil. api_exchanges relie chaque requête aux model_inputs et model_outputs. Une contrainte interdit de dupliquer une ligne d'entrée au sein d'un échange. La vue api_logs expose une lecture plus pratique. Le rôle applicatif ne peut pas modifier les sources ni supprimer les traces.

Source : Sources : database.py ; docs/database.md ; docs/schema.sql

## 11 — Une requête peut être expliquée et retrouvée

Chaque requête reçoit un identifiant unique X-Request-ID. Le journal conserve la route, le contexte utile, les dates, la durée, le fichier, le nombre de lignes, la version du modèle et les erreurs. Les étapes persistées permettent de voir où un traitement s'est arrêté. Un échec du modèle conserve les inputs. Si la BDD n'est pas accessible dès le départ, l'API refuse le calcul et l'erreur ne peut être écrite que dans les logs du processus. Un arrêt brutal peut laisser pending ; il n'y a pas de garantie exactement une fois.

Source : Sources : audit.py ; api.py ; docs/api_logs.md

## 12 — Trois routes CSV au cœur d'une API de sept endpoints

Présenter les trois routes demandées pour le fichier : predict/file renvoie les classes natives ; predict-proba/file renvoie les probabilités dans l'ordre de classes ; score/file exige les vraies réponses et renvoie l'accuracy native et les métriques au seuil optimisé. Les routes JSON et par ID utilisent le seuil optimisé. Les deux endpoints techniques sont health et features. L'ordre des lignes est conservé. Les CSV doivent être UTF-8 et leur contenu est limité à dix Mio. Swagger permet de sélectionner un fichier et de tester une route.

Source : Sources : api.py ; docs/api.md ; docs/openapi.json

## 13 — Pydantic valide les entrées et les sorties

La validation est partagée entre le JSON et chaque ligne CSV. Elle contrôle les noms de variables selon le modèle, la présence de valeurs numériques finies et les cibles binaires. Les booléens et valeurs nulles ne sont pas acceptés comme nombres. Les sorties sont contrôlées avant insertion : classe entière 0 ou 1, probabilités bornées dont la somme vaut un à la tolérance près, dimensions cohérentes et métriques bornées. Pydantic assure le respect du contrat, pas la performance statistique ni toutes les règles métier.

Source : Sources : schemas.py ; docs/api_validation.md

## 14 — Tester le service sans confondre tests et performance ML

La suite vérifiée contient 87 tests et la couverture des modules suivis est arrondie à 89 %. Chaque endpoint dispose de cas valides et invalides. Les modèles simulés permettent de fixer précisément les réponses attendues. Les tests de BDD vérifient la relecture des inputs committés avant calcul, les sorties persistées et le comportement en cas d'échec. La CI utilise PostgreSQL avec un schéma isolé par test. Ces tests logiciels ne constituent pas une mesure de généralisation du modèle.

Source : Sources : tests/ ; rapports de vérification du projet ; docs/api_validation.md

## 15 — Le push déclenche une publication contrôlée

À chaque push ou pull request, la pipeline vérifie les tests avec PostgreSQL, la documentation et le package. L'export préparé ne conserve que model, threshold, feature_names et positive_class. Les lignes individuelles ne sont pas publiées avec cet export. Sur main, après validation d'environnement, le job transmet les quatre fichiers à SamGabb/hrnova avec le secret HF_TOKEN. Cela ne réentraîne pas le modèle et ne crée pas une API hébergée. Les protections de branche doivent être configurées dans GitHub pour bloquer les fusions.

Source : Sources : .github/workflows/ci.yml ; docs/huggingface.md ; docs/deployment.md

## 16 — Une documentation pour utiliser et maintenir le projet

La documentation comporte douze pages MkDocs avec navigation et recherche. Elle distingue le parcours utilisateur, les contrats API et les informations développeur. Swagger et ReDoc décrivent les endpoints ; le contrat OpenAPI peut être exporté sans connexion BDD. Les guides détaillent les performances historiques et leurs limites, le schéma, les logs, l'installation, le déploiement et le protocole de maintenance. La CI construit le site en mode strict et conserve l'HTML comme artefact ; elle ne publie pas automatiquement un site public.

Source : Sources : mkdocs.yml ; docs/index.md ; README.md

## 17 — Les limites définissent les prochaines priorités

La première priorité est d'apprendre les transformations uniquement sur le train et dans chaque fold, puis de sérialiser l'ensemble de la préparation. Aujourd'hui, les médianes et l'encodeur nominal sont calculés avant le split ; cela peut influencer les résultats. Il faut ensuite confirmer les performances sur des données temporelles ou externes, car le test actuel ne comporte que 47 départs. Une analyse des erreurs par sous-population est nécessaire. Enfin, le service est local et sans authentification HTTP : son exposition distante demanderait un travail spécifique.

Source : Sources : docs/model.md ; docs/maintenance.md ; docs/deployment.md

## 18 — Un modèle exploitable, un résultat vérifiable

Conclure sur les éléments réellement livrés : modèle calibré, API validée, données et échanges structurés en BDD, tests, documentation et publication contrôlée du modèle. Le rappel augmente avec le seuil optimisé, mais les performances demeurent limitées et doivent être confirmées après correction de la préparation. La suite logique est une pipeline de prétraitement réutilisable, une validation indépendante et une exploitation surveillée. Inviter aux questions ou proposer la démonstration en annexe.

Source : Sources : documentation du projet et résultats vérifiés

## 19 — Démonstration : du fichier au journal de requête

Avant la soutenance, démarrer PostgreSQL et l'API. Ouvrir Swagger pour montrer les sept endpoints. Envoyer le CSV synthétique aux routes predict-proba/file puis score/file. Expliquer que les cibles de l'exemple sont fictives et que le score obtenu n'est pas une mesure de performance. Relever le X-Request-ID et retrouver le journal, les inputs et les outputs dans PostgreSQL. Terminer avec une requête invalide pour montrer le code 422 et la cause dans api_logs. Ne jamais afficher .env ou les tokens pendant la démonstration.

Source : Sources : examples/ ; docs/api.md ; docs/api_logs.md

## 20 — Sources et éléments de preuve

Les chiffres du modèle proviennent des sorties enregistrées dans le notebook et du relevé model_metrics.json, associé au hash de l'artefact. Le rapport de tests prouve la conformité logicielle, pas la performance statistique. Le contrat OpenAPI et la documentation sont construits depuis les sources. Les liens GitHub et Hugging Face permettent de retrouver le projet et la version publiée ; leur accessibilité dépend des droits du visiteur.

Source : Références du projet • état examiné le 27 octobre 2026
