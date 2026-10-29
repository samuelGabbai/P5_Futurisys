# Déploiement par environnement — Notes pour l’oral

## 1. Un environnement = une instance et sa configuration

Un environnement associe le code de l’API, sa configuration, sa base PostgreSQL et une version du modèle. Development sert à développer, staging à répéter la mise en service et production à servir les utilisateurs. Chaque cible doit disposer de ses accès et de sa base, pour éviter que les tests écrivent dans les données de production. Le code peut être identique ; les paramètres changent. Dans HRNova, l’API actuellement disponible reste l’instance locale. Les trois environnements GitHub existants organisent les validations sans créer trois serveurs.

Sources : docs/deployment.md · .github/workflows/ci.yml

## 2. Du push à la mise en production

Le parcours cible commence par une branche de travail et des contrôles CI. Une pull request permet de revoir les changements. Le candidat est testé en préproduction avant une validation de mise en production. L’objectif est de promouvoir les mêmes artefacts validés, identifiés par un commit Git et un hash de modèle. Si la fusion change le code, le nouveau candidat doit être vérifié. Après déploiement, contrôler la santé de l’API, une prédiction et sa trace en base. Ce protocole décrit une cible d’exploitation ; la pipeline actuelle ne réalise pas de déploiement distant de FastAPI.

Source : docs/deployment.md — protocole cible

## 3. GitHub Environments : variables, secrets et règles

Le workflow sélectionne development pour les branches de travail, staging pour develop et production pour main, lors des push ou lancements manuels. Les pull requests exécutent les tests sans accéder à ces environnements. Chaque environnement GitHub peut contenir des variables et secrets propres et des règles de branches. Les approbations requises dépendent des fonctionnalités disponibles pour le dépôt. Le job environment-validation utilise une base PostgreSQL de test éphémère, vérifie le chemin du modèle puis relance les tests. Sur main, le job de publication utilise production pour envoyer le modèle vers SamGabb/hrnova. Il ne démarre pas de serveur API.

Source : .github/workflows/ci.yml · docs/deployment.md

## 4. Configurer, vérifier et pouvoir revenir en arrière

DATABASE_URL doit pointer vers la base propre à la cible et HRNOVA_MODEL_PATH vers le fichier validé. Les fichiers .env.staging et .env.production ne sont pas versionnés. L’exemple suppose que la préproduction, ses tables, ses droits et son modèle ont déjà été préparés. Uvicorn écoute ici uniquement en local sur un port distinct. Avant de mettre en service une version, sauvegarder la base et conserver les références de l’ancienne version. Après démarrage, vérifier /health puis une inférence tracée. En cas d’incident, revenir au code et au modèle précédents ; une migration de schéma peut nécessiter un traitement supplémentaire. Aucun serveur de production n’est provisionné par cet exemple.

Sources : docs/deployment.md · docs/maintenance.md
