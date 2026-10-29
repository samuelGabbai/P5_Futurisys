# Git, Pydantic et PostgreSQL — Notes pour l’oral

12 diapositives. Les notes sont aussi intégrées au PowerPoint.

## 01 — Git garde l’histoire ; GitHub la partage

Git est le logiciel de gestion de versions. Il fonctionne en local : chaque commit conserve un état du projet et ses liens avec les commits précédents. GitHub héberge une copie distante du dépôt et apporte les pull requests. GitHub Actions exécute des workflows sur des machines appelées runners. Un commit local ne lance pas à lui seul les tests sur GitHub : il faut notamment un push et un workflow configuré pour cet événement.

Source : https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F

## 02 — Du fichier modifié au dépôt distant

Le répertoire de travail contient les fichiers que l’on modifie. git add sélectionne les changements à enregistrer et les place dans l’index. git commit crée un instantané local avec un message, un auteur et un parent. git push transmet les commits à la branche distante. git status permet de vérifier chaque étape. Une fois un fichier ajouté, une nouvelle modification doit être ajoutée à nouveau pour entrer dans le prochain commit. Ne jamais versionner de jetons ni le fichier .env.

Source : https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F

## 03 — Branches : proposer, vérifier, puis fusionner

Une branche est une référence vers un commit, pas une copie indépendante du dossier. Créer une branche permet de développer une fonctionnalité sans faire évoluer main immédiatement. Après le push, la pull request présente les différences, les contrôles et les commentaires. Les conflits surviennent lorsque Git ne peut pas combiner automatiquement des modifications ; il faut choisir le contenu correct et enregistrer la résolution. Les vérifications obligatoires et la protection de main se configurent dans GitHub : le YAML seul ne bloque pas les fusions.

Source : https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F

## 04 — GitHub Actions : que se passe-t-il au push ?

Un workflow est un fichier YAML sous .github/workflows. Il définit les événements, les jobs et leurs étapes. Chaque job s’exécute sur un runner ; les étapes d’un même job s’enchaînent. Les jobs peuvent fonctionner en parallèle, sauf dépendance déclarée avec needs. Dans HRNova, la CI vérifie le projet et l’intégration PostgreSQL. La publication Hugging Face envoie les artefacts préparés vers SamGabb/hrnova ; elle ne réentraîne pas automatiquement le modèle. Le jeton est fourni par les secrets GitHub au job de publication, jamais écrit dans le dépôt.

Source : https://docs.github.com/en/actions/get-started/understand-github-actions

## 05 — Pydantic transforme une entrée en contrat

Pydantic décrit la structure et les types attendus. Il vérifie la donnée et peut la convertir selon les règles choisies. Les exemples de cette diapositive montrent un seul champ numérique : une vraie requête HRNova doit également fournir toutes les variables attendues. Le projet accepte une chaîne numérique convertible et rejette les booléens, les valeurs absentes et les nombres non finis. Certaines de ces règles sont des validateurs spécifiques à HRNova ; elles ne sont pas toutes les valeurs par défaut de Pydantic. La validation technique ne garantit pas la qualité statistique de la prédiction.

Source : https://docs.pydantic.dev/latest/concepts/validators/

## 06 — Un schéma Python décrit les données attendues

Cet extrait est volontairement simplifié : la version complète est dans schemas.py. NumericValue associe un nombre fini à un validateur exécuté avant la conversion. Le validateur numeric_value rejette notamment les booléens et les valeurs nulles. Field(min_length=1) impose au moins une variable. ConfigDict(extra='forbid') rejette les champs supplémentaires à la racine du modèle. Un autre validateur du projet compare les clés de features à la liste exacte des variables attendues : il détecte les variables manquantes et inconnues. Ce dernier contrôle n’est pas assuré par extra='forbid' dans un dictionnaire.

Source : Code du projet : schemas.py · https://docs.pydantic.dev/latest/concepts/validators/

## 07 — Un fichier CSV passe les mêmes contrôles

Le fichier envoyé à l’API est décodé puis transformé en lignes. Chaque ligne est soumise au schéma de prédiction ; le lot doit contenir au moins une ligne. Le projet vérifie les variables attendues, convertit les valeurs numériques et prépare les colonnes dans l’ordre du modèle. Une erreur est renvoyée avec un contexte exploitable pour retrouver la ligne et le champ. Le modèle n’est pas appelé si l’entrée est invalide. Pour score, les cibles doivent aussi être valides et alignées avec les lignes : les formes acceptées sont Non/Oui ou 0/1 selon les règles du projet.

Source : Code du projet : schemas.py, inference.py

## 08 — Valider aussi ce que renvoie le modèle

La validation continue après le calcul. Le projet impose des classes binaires 0 et 1 pour les prédictions, des probabilités finies dans l’intervalle [0,1] et une somme par ligne égale à 1 à une tolérance de 10 puissance moins 6. Les réponses par fichier doivent avoir le bon nombre de lignes. Les métriques sont également contrôlées. Une sortie invalide provoque une erreur 500 et une trace d’échec ; les entrées déjà enregistrées restent disponibles, mais aucune sortie invalide n’est sauvegardée comme résultat. Pydantic contrôle le contrat de réponse, pas la pertinence métier ni la performance sur de nouvelles données.

Source : Code du projet : schemas.py, inference.py

## 09 — PostgreSQL : où vivent les données ?

PostgreSQL est le serveur qui stocke les données et exécute les requêtes SQL. Dans la configuration locale du projet, le serveur est joint sur 127.0.0.1 au port 5433 et la base s’appelle hrnova. Une base contient des schémas, dont public ; les schémas contiennent des tables. Une table possède des colonnes typées et des lignes. DBeaver est un client pour se connecter au serveur et explorer ces objets. Installer DBeaver ne démarre pas PostgreSQL et ne crée pas la base. Les paramètres de connexion restent configurables par l’environnement ; aucun mot de passe n’est inclus ici.

Source : Configuration et modèles de données du projet

## 10 — Les clés relient les tables entre elles

Une clé primaire identifie une ligne de manière unique. Une clé étrangère pointe vers une ligne d’une autre table et empêche de créer un lien vers un identifiant inexistant. L’exemple emploie l’identifiant fictif 42. Dans HRNova, employees.id_employee est relié aux tables d’enquêtes et d’évaluations par employee_id. Les échanges API possèdent également leur identifiant ; les entrées et les sorties y sont rattachées. La paire exchange_id et row_index est unique pour les entrées d’un échange. SQLAlchemy traduit les objets Python en SQL, puis PostgreSQL applique les contraintes. JSONB permet de stocker les variables et résultats structurés.

Source : Modèles SQLAlchemy du projet

## 11 — Une transaction protège un groupe d’écritures

Une transaction regroupe des instructions SQL : commit les rend durables, rollback les annule en cas d’échec. Les garanties ACID couvrent l’atomicité, la cohérence des contraintes, l’isolation et la durabilité. Elles s’appliquent à chaque transaction, pas automatiquement à l’ensemble d’une requête HTTP. Dans HRNova, les entrées sont validées et commitées avant le calcul, puis relues depuis la base. Le modèle produit une sortie qui est validée, enregistrée puis relue. Cela conserve les entrées en cas d’échec ultérieur. Si PostgreSQL est indisponible, l’inférence ne doit pas contourner la base ; si la sortie ne peut pas être enregistrée, elle n’est pas livrée comme un succès.

Source : https://www.postgresql.org/docs/18/tutorial-transactions.html

## 12 — Tracer un appel : retrouver son parcours en SQL

api_exchanges décrit la requête et son déroulement. model_inputs conserve les entrées validées, model_outputs les résultats valides, et model_versions identifie le modèle. L’identifiant de requête permet de corréler ces tables et les logs. La vue api_logs présente une lecture simplifiée des échanges ; une vue est une requête sauvegardée, pas une duplication des traces. Les requêtes rejetées gardent une trace d’erreur, même sans entrée modèle valide. Le rôle applicatif doit disposer des seuls droits nécessaires. Un échec total de la base empêche évidemment d’écrire cette trace en base : les logs applicatifs complètent alors l’investigation.

Source : Schéma PostgreSQL du projet · vue public.api_logs
