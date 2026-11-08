# HRNova — Notes actualisées au 4 novembre 2026

34 diapositives ; notes intégrées au PowerPoint.

## 01 — Du modèle à une API sécurisée et traçable

Le projet relie un modèle calibré à une API locale validée, une base PostgreSQL et une chaîne CI/CD. L’état technique est actualisé au 4 novembre 2026. Les performances prédictives restent celles du notebook évalué en octobre et sont distinctes des mesures HTTP récentes. Le déploiement local répond au référentiel ; le build Docker réel reste à confirmer sur GitHub Actions.

Sources : État technique : 4 novembre 2026 • Métriques ML historiques : octobre 2026

## 02 — Un outil d'aide à l'analyse RH

L'objectif est de mieux comprendre et repérer les situations associées aux départs. La cible connue est binaire : salarié resté ou parti. Le résultat est une probabilité et une décision selon un seuil. Souligner que le modèle ne prouve pas les causes de départ et ne remplace pas une analyse métier. Il faut relier les fausses alertes et les départs manqués à des coûts et à des actions définies avec les RH.

Sources : Sources : README.md ; docs/model.md

## 03 — Trois sources, une population de 1 470 salariés

Les trois fichiers ont chacun 1 470 lignes, mais concernent la même population : on ne dispose pas de 4 410 salariés différents. Les clés sont rapprochées entre les sources, tout en conservant leur représentation d'origine en base. La classe positive représente 237 départs sur 1 470, soit environ 16,1 %. Le déséquilibre justifie de regarder précision, rappel et F1, pas uniquement l'accuracy.

Sources : Sources : Data/*.csv ; docs/model.md ; docs/database.md

## 04 — Transformer les données en 43 variables numériques

La préparation est exécutée dans le notebook. Elle fusionne les sources, convertit les pourcentages, encode les variables et crée notamment des indicateurs de rémunération relative et une satisfaction moyenne. La cible et les identifiants sont exclus des variables explicatives. L'API reçoit le résultat de cette préparation ; elle ne fait pas la transformation d'un fichier RH brut. Certaines références sont aujourd'hui calculées avant le split : cette limite sera détaillée plus loin.

Sources : Sources : notebook, cellules 12 à 28 ; docs/features.md

## 05 — Séparer l'évaluation du choix du seuil

La séparation stratifiée réserve 20 % des données pour le test : 294 salariés dont 47 départs. Le train compte 1 176 salariés dont 190 départs. Les modèles sont comparés par validation croisée à cinq folds ; la grille optimise le F1 et la calibration utilise sigmoid avec cinq folds. Le seuil est choisi sur les probabilités out-of-fold du train. Les transformations apprises avant le split limitent toutefois l'indépendance globale de l'évaluation actuelle.

Sources : Sources : notebook, cellules 28 à 41 ; docs/model.md

## 06 — Comparer plusieurs approches, sans surinterpréter le
classement

Cette comparaison utilise les F1 moyens en validation croisée enregistrés dans le notebook. LightGBM atteint ici le meilleur F1 moyen, tandis que la régression logistique est également compétitive. La forêt optimisée est le modèle exporté, mais il ne faut pas affirmer sa supériorité générale. Les écarts-types et les protocoles de choix des hyperparamètres doivent être pris en compte. Aucune comparaison finale sur le test de tous les concurrents avec des seuils optimisés identiquement n'est fournie.

Sources : Sources : notebook, cellules 31, 34, 54 et 55 ; docs/model.md

## 07 — Le modèle livré : forêt régularisée et probabilités calibrées

La grille explore 16 combinaisons, évaluées sur cinq folds. Le modèle retenu utilise 300 arbres avec une profondeur maximale de cinq, un minimum de cinq observations pour une séparation et deux par feuille. La pondération des classes est balanced. La calibration sigmoid est réalisée avec CalibratedClassifierCV, cv=5. Le fichier complet conserve aussi le seuil, les noms de variables, la classe positive et les variables préparées des salariés pour l'import local.

Sources : Sources : artefact local ; docs/model.md ; notebook, cellules 34 et 36

## 08 — Le seuil optimisé augmente le rappel sur le test

Sur les 294 salariés du test, le rappel passe de 17,0 % à 61,7 % lorsque le seuil passe de 0,50 à environ 0,2232. Le F1 augmente de 0,229 à 0,500. La précision reste de 42,0 % : toutes les alertes ne sont pas de vrais départs. L'accuracy au seuil optimisé est de 80,27 % et la ROC-AUC de 0,7692. Une stratégie qui prédit toujours resté atteindrait déjà 84,0 % d'accuracy sur ce test : l'accuracy seule ne suffit pas. Les valeurs viennent du notebook, sans réévaluation pendant la fabrication du support.

Sources : Source : notebook, cellule 41 ; docs/model_metrics.json • test : 294 lignes, 47 départs

## 09 — Fonctionnement des requêtes

Le client fournit du JSON, un CSV préparé ou un identifiant salarié. FastAPI et Pydantic valident le contrat. Le service enregistre les inputs en PostgreSQL, les relit dans une nouvelle session, puis appelle le modèle. Les outputs sont validés, committés et relus avant la réponse HTTP. Toutes les routes d'inférence passent par ce service. Ce choix ajoute des accès BDD mais garantit que les valeurs effectivement calculées sont celles stockées.

Sources : Sources : api.py ; schemas.py ; inference.py ; docs/architecture.md

## 10 — PostgreSQL structure les données et l'historique

La BDD contient huit tables. Les sources sont employees, surveys et evaluations, reliées par identifiant salarié. prepared_employees conserve les variables par salarié et version de modèle. model_versions conserve le SHA-256, les noms de variables et le seuil. api_exchanges relie chaque requête aux model_inputs et model_outputs. Une contrainte interdit de dupliquer une ligne d'entrée au sein d'un échange. La vue api_logs expose une lecture plus pratique. Le rôle applicatif ne peut pas modifier les sources ni supprimer les traces.

Sources : Sources : database.py ; docs/database.md ; docs/schema.sql

## 11 — Des besoins BI définis et deux vues SQL

Le référentiel demande de décrire les besoins analytiques. Le projet définit les utilisateurs, décisions, KPI, sources, fréquences et droits, et fournit deux vues SQL sans prétendre qu’une interface de dashboard est hébergée. La vue technique agrège activité, statuts, latence et volumes. La vue métier agrège les scores unitaires par date, hash et seuil, en masquant les groupes de moins de cinq requêtes. Une requête n’est pas un salarié unique ; la fréquence des alertes n’est pas le turnover réel. Le compte SQL du service ne doit pas être distribué aux utilisateurs BI : un rôle dédié doit être provisionné avec seulement SELECT sur les vues nécessaires.

Sources : Sources : docs/analytics.md • docs/migrations/003_analytics_views.sql

## 12 — PostgreSQL : où sauvegarde les données ?

PostgreSQL est le serveur qui stocke les données et exécute les requêtes SQL. Dans la configuration locale du projet, le serveur est joint sur 127.0.0.1 au port 5433 et la base s’appelle hrnova. Une base contient des schémas, dont public ; les schémas contiennent des tables. Une table possède des colonnes typées et des lignes. DBeaver est un client pour se connecter au serveur et explorer ces objets. Installer DBeaver ne démarre pas PostgreSQL et ne crée pas la base. Les paramètres de connexion restent configurables par l’environnement ; aucun mot de passe n’est inclus ici.

Sources : Configuration et modèles de données du projet

## 13 — Les clés relient les tables entre elles

Une clé primaire identifie une ligne de manière unique. Une clé étrangère pointe vers une ligne d’une autre table et empêche de créer un lien vers un identifiant inexistant. L’exemple emploie l’identifiant fictif 42. Dans HRNova, employees.id_employee est relié aux tables d’enquêtes et d’évaluations par employee_id. Les échanges API possèdent également leur identifiant ; les entrées et les sorties y sont rattachées. La paire exchange_id et row_index est unique pour les entrées d’un échange. SQLAlchemy traduit les objets Python en SQL, puis PostgreSQL applique les contraintes. JSONB permet de stocker les variables et résultats structurés.

Sources : Modèles SQLAlchemy du projet

## 14 — Traçabilité de la requête

Chaque requête reçoit un identifiant unique X-Request-ID. Le journal conserve la route, le contexte utile, les dates, la durée, le fichier, le nombre de lignes, la version du modèle et les erreurs. Les étapes persistées permettent de voir où un traitement s'est arrêté. Un échec du modèle conserve les inputs. Si la BDD n'est pas accessible dès le départ, l'API refuse le calcul et l'erreur ne peut être écrite que dans les logs du processus. Un arrêt brutal peut laisser pending ; il n'y a pas de garantie exactement une fois.

Sources : Sources : audit.py ; api.py ; docs/api_logs.md

## 15 — Neuf routes, des accès selon le rôle

Distinguer les cinq routes d’inférence, les routes de contrat et d’identité, et la livraison du modèle. /health reste public. Les comptes utilisateur et admin accèdent aux API métier, tandis que livreur et admin peuvent télécharger le modèle. Les anciens rôles lecteur et analyste restent compatibles avec leurs permissions plus limitées. Les trois routes CSV partagent les contrôles de format et la traçabilité.

Sources : Sources : api.py • auth.py • docs/openapi.json

## 16 — Deux droits distincts : utiliser et livrer

Le contrôle d’accès est appliqué par dépendance FastAPI. Le rôle utilisateur autorise les API métier, notamment le score par identifiant salarié ; il ne permet pas de télécharger ni publier le modèle. Le rôle livreur possède uniquement le droit de livraison. Admin cumule les deux. HTTP Basic vérifie le mot de passe haché à chaque appel. Un compte absent ou désactivé est refusé ; un mauvais rôle produit 403. Le token Hugging Face reste nécessaire en plus du droit applicatif pour publier.

Sources : Sources : auth.py • docs/authentication.md

## 17 — Se connecter comme utilisateur simple

PostgreSQL doit être démarré avant l’API. La commande Uvicorn est commune à tous les rôles : le rôle dépend du compte qui s’authentifie, pas d’une option de lancement. Dans Swagger, utiliser Authorize avec application. Le secret aléatoire est disponible uniquement dans le fichier local protégé, sans l’afficher pendant la soutenance. Le script bootstrap crée les comptes une fois et préserve une configuration existante. /auth/me permet de vérifier que le rôle effectif est utilisateur.

Sources : Sources : scripts/manage_users.py • docs/installation.md • docs/authentication.md

## 18 — Livrer un modèle sans exporter les lignes RH

L’archive de livraison utilise une liste de clés autorisées : modèle, seuil, variables et classe positive. Les autres champs, dont records_by_employee_id, sont exclus. Elle comporte aussi les hashes et les versions de bibliothèques. Le même export est utilisé pour le téléchargement et Hugging Face. Le script de publication vérifie un compte livreur ou admin avant tout appel distant, puis utilise un token HF autorisé en écriture. Publier n’entraîne pas le modèle et ne déploie pas l’API. L’exclusion des lignes source ne garantit pas à elle seule l’anonymisation du modèle appris.

Sources : Sources : model_release.py • scripts/publish_huggingface.py • docs/huggingface.md

## 19 — Pydantic valide les entrées et les sorties

La validation est partagée entre le JSON et chaque ligne CSV. Elle contrôle les noms de variables selon le modèle, la présence de valeurs numériques finies et les cibles binaires. Les booléens et valeurs nulles ne sont pas acceptés comme nombres. Les sorties sont contrôlées avant insertion : classe entière 0 ou 1, probabilités bornées dont la somme vaut un à la tolérance près, dimensions cohérentes et métriques bornées. Pydantic assure le respect du contrat, pas la performance statistique ni toutes les règles métier.

Sources : Sources : schemas.py ; docs/api_validation.md

## 20 — Pydantic : Contrôle des entrées

Pydantic décrit la structure et les types attendus. Il vérifie la donnée et peut la convertir selon les règles choisies. Les exemples de cette diapositive montrent un seul champ numérique : une vraie requête HRNova doit également fournir toutes les variables attendues. Le projet accepte une chaîne numérique convertible et rejette les booléens, les valeurs absentes et les nombres non finis. Certaines de ces règles sont des validateurs spécifiques à HRNova ; elles ne sont pas toutes les valeurs par défaut de Pydantic. La validation technique ne garantit pas la qualité statistique de la prédiction.

Sources : https://docs.pydantic.dev/latest/concepts/validators/

## 21 — Un schéma Python décrit les données attendues

Cet extrait est volontairement simplifié : la version complète est dans schemas.py. NumericValue associe un nombre fini à un validateur exécuté avant la conversion. Le validateur numeric_value rejette notamment les booléens et les valeurs nulles. Field(min_length=1) impose au moins une variable. ConfigDict(extra='forbid') rejette les champs supplémentaires à la racine du modèle. Un autre validateur du projet compare les clés de features à la liste exacte des variables attendues : il détecte les variables manquantes et inconnues. Ce dernier contrôle n’est pas assuré par extra='forbid' dans un dictionnaire.

Sources : Code du projet : schemas.py · https://docs.pydantic.dev/latest/concepts/validators/

## 22 — Un fichier CSV passe les mêmes contrôles

Le fichier envoyé à l’API est décodé puis transformé en lignes. Chaque ligne est soumise au schéma de prédiction ; le lot doit contenir au moins une ligne. Le projet vérifie les variables attendues, convertit les valeurs numériques et prépare les colonnes dans l’ordre du modèle. Une erreur est renvoyée avec un contexte exploitable pour retrouver la ligne et le champ. Le modèle n’est pas appelé si l’entrée est invalide. Pour score, les cibles doivent aussi être valides et alignées avec les lignes : les formes acceptées sont Non/Oui ou 0/1 selon les règles du projet.

Sources : Code du projet : schemas.py, inference.py

## 23 — Valider aussi ce que renvoie le modèle

La validation continue après le calcul. Le projet impose des classes binaires 0 et 1 pour les prédictions, des probabilités finies dans l’intervalle [0,1] et une somme par ligne égale à 1 à une tolérance de 10 puissance moins 6. Les réponses par fichier doivent avoir le bon nombre de lignes. Les métriques sont également contrôlées. Une sortie invalide provoque une erreur 500 et une trace d’échec ; les entrées déjà enregistrées restent disponibles, mais aucune sortie invalide n’est sauvegardée comme résultat. Pydantic contrôle le contrat de réponse, pas la pertinence métier ni la performance sur de nouvelles données.

Sources : Code du projet : schemas.py, inference.py

## 24 — Une recette complète sur PostgreSQL

La recette finale exécute 239 tests sur PostgreSQL dans une base temporaire qui est supprimée à la fin, sans vider hrnova. Aucun test n’est ignoré. La couverture de 97.88 % porte sur les huit modules applicatifs et les scripts opérationnels ; les générateurs de présentations sont exclus. Le seuil CI est 95 %. Les tests couvrent les erreurs, transactions, authentification, volumes et vues analytiques. Le rapport BDD réel valide les cinq routes, les 1 470 lignes par source et les privilèges SQL limités. La couverture ne remplace pas un vrai test de déploiement Docker.

Sources : Sources : docs/test_results.json • docs/database_validation.json • docs/validation.md

## 25 — Mesurer la latence et le débit du service

Le benchmark utilise le modèle réel, HTTP Basic et PostgreSQL, y compris les transactions de traçabilité. Chaque scénario comporte un préchauffage exclu et huit appels mesurés, soit 48 requêtes sans erreur. La machine est un Mac ARM64 de dix CPU avec un processus Uvicorn. La concurrence augmente le débit et la latence ; le p95 sur huit observations reste une estimation indicative, pas un SLA ni un test d’endurance. Les valeurs présentées proviennent du JSON de mesure et sont distinctes des métriques prédictives historiques.

Sources : Source : docs/performance_results.json • macOS ARM64, 10 CPU • 8 requêtes par scénario

## 26 — Du push aux contrôles avant livraison

Le job principal installe les dépendances verrouillées, lance les tests PostgreSQL, construit le package et la documentation, puis initialise la base du contrôle Docker. Il crée des comptes temporaires, construit réellement l’image et teste ses routes HTTP et permissions. Ce contrôle est prévu aussi pour les pull requests. Le contexte Docker a été corrigé pour inclure auth.py et model_release.py. Docker étant absent de la machine locale, le vrai build doit être confirmé par la prochaine exécution GitHub Actions. La publication et le déploiement restent conditionnés aux environnements, secrets et runners configurés.

Sources : Sources : .github/workflows/ci.yml • .dockerignore • scripts/smoke_container.py

## 27 — Trois cibles, des secrets et un retour arrière

La cible démontrée est locale, ce qui est accepté par le référentiel actualisé. development, staging et production séparent configurations, bases et secrets. Le test est fourni par un job PostgreSQL isolé et une base jetable locale. La mise en service Docker est conditionnée à ENABLE_API_DEPLOYMENT=true et à des runners préparés. Le précontrôle vérifie la base et le modèle, une prédiction authentifiée suit le démarrage et un échec tente de restaurer l’image précédente. Les réglages de protection de branches et d’approbation GitHub doivent être configurés dans le service ; le YAML ne les active pas automatiquement.

Sources : Sources : deployment/ • scripts/deploy_api.py • docs/deployment.md

## 28 — GIT

Git est le logiciel de gestion de versions. Il fonctionne en local : chaque commit conserve un état du projet et ses liens avec les commits précédents. GitHub héberge une copie distante du dépôt et apporte les pull requests. GitHub Actions exécute des workflows sur des machines appelées runners. Un commit local ne lance pas à lui seul les tests sur GitHub : il faut notamment un push et un workflow configuré pour cet événement.

Sources : https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F

## 29 — Git : des changements lisibles et vérifiables

Le nettoyage retire du suivi neuf artefacts générés tout en conservant leurs fichiers locaux : .DS_Store, bytecode, métadonnées egg-info et couverture. .editorconfig et CONTRIBUTING définissent la structure et les conventions. Les prochains commits décrivent le problème, le changement et la validation ; l’historique existant n’est pas réécrit. Le modèle de pull request demande les tests, les secrets ou migrations concernés sans leurs valeurs et le retour arrière éventuel. Les changements actuels doivent ensuite être committés et poussés pour déclencher la CI distante.

Sources : Sources : CONTRIBUTING.md • .editorconfig • .github/pull_request_template.md

## 30 — Rajout d’un screen record de test de l’API

Le répertoire de travail contient les fichiers que l’on modifie. git add sélectionne les changements à enregistrer et les place dans l’index. git commit crée un instantané local avec un message, un auteur et un parent. git push transmet les commits à la branche distante. git status permet de vérifier chaque étape. Une fois un fichier ajouté, une nouvelle modification doit être ajoutée à nouveau pour entrer dans le prochain commit. Ne jamais versionner de jetons ni le fichier .env.

Sources : https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F

## 31 — GitHub Actions : ce qui est réellement automatisé

Les événements push, pull_request et merge_group déclenchent la validation. Les étapes d’un job s’enchaînent ; needs impose les dépendances entre jobs. Le contrôle principal comprend désormais Docker et un smoke HTTP avec PostgreSQL. Les jobs de publication du modèle et de déploiement API sont distincts. La protection des branches et les approbations sont des réglages GitHub à activer ; la présence du YAML ne prouve pas leur activation. Ne pas annoncer le build Docker comme exécuté localement puisqu’il doit être confirmé dans GitHub Actions.

Sources : Source : .github/workflows/ci.yml • docs/validation.md

## 32 — Une documentation pour utiliser et maintenir le projet

La documentation inclut maintenant l’authentification, les besoins analytiques, les performances et les preuves de recette. Swagger permet de tester le rôle utilisateur et les guides distinguent les résultats vérifiés localement des contrôles Docker à confirmer dans GitHub Actions.

## 33 — Des acquis vérifiés et des limites explicites

La préparation sans fuite et la validation indépendante restent les priorités du modèle. Les limites de prétraitement historique ne sont pas corrigées par les tests logiciels. L’authentification et les rôles sont désormais présents pour l’usage local. Une exposition distante exige HTTPS, limitation des tentatives, supervision et habilitations adaptées. Les mesures actuelles ne sont pas une garantie de capacité maximale. Les besoins analytiques sont formalisés ; une connexion BI avec rôle SQL dédié reste à provisionner selon le SI cible.

Sources : Sources : docs/model.md • docs/performance.md • docs/analytics.md • docs/validation.md

## 34 — Démonstration : du fichier au journal de requête

Avant la soutenance, démarrer PostgreSQL et l'API. Ouvrir Swagger pour montrer les neuf endpoints. Envoyer le CSV synthétique aux routes predict-proba/file puis score/file. Expliquer que les cibles de l'exemple sont fictives et que le score obtenu n'est pas une mesure de performance. Relever le X-Request-ID et retrouver le journal, les inputs et les outputs dans PostgreSQL. Terminer avec une requête invalide pour montrer le code 422 et la cause dans api_logs. Ne jamais afficher .env ou les tokens pendant la démonstration.

Sources : Sources : examples/ ; docs/api.md ; docs/api_logs.md
