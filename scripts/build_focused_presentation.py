"""Support de 19 slides suivant le plan de soutenance demandé.

PYTHONPATH=/private/tmp/hrnova-plan-slides .venv/bin/python scripts/build_focused_presentation.py
Dépendances de génération : python-pptx==1.0.2 et Pillow.
"""
import json
from datetime import datetime
from PIL import Image
from build_presentation import Deck, ROOT, NAVY, TEAL, WHITE, INK, LIME

OUT = ROOT / 'presentations'
STEM = 'HRNova_Soutenance_Plan_2026-11-10'
d = Deck(total=19)
d.prs.core_properties.created = datetime(2026, 11, 10)
tests = json.loads((ROOT / 'docs/test_results.json').read_text())

def new(title, section, notes, source):
    d.new(title, section, notes, source)

def cards(left, right, banner=None):
    d.card(.55, 1.95, 5.95, 3.75, left[0], left[1], size=20)
    d.card(6.8, 1.95, 5.95, 3.75, right[0], right[1], size=20)
    if banner:
        d.banner(banner, y=6.05)
    d.finish()

new('HRNova : rendre le modèle utilisable', '01 / Contexte du projet',
    'Le projet MLOps transforme un modèle RH déjà entraîné en service local. L’objectif est de proposer des prédictions contrôlées, de conserver leurs entrées et sorties et de rendre les livraisons reproductibles. Le référentiel fourni accepte le déploiement local. La publication distante reste conditionnée à la configuration des services.',
    'README.md • docs/architecture.md • Référentiel de la mission')
d.text('Du notebook à un service sécurisé, testé et traçable.', .65, 1.95, 12, .65, 26, TEAL, True)
for i, (a,b) in enumerate([('SERVIR','FastAPI + Pydantic\nJSON, CSV, salarié par ID'),('TRACER','PostgreSQL + SQLAlchemy\nEntrées, sorties et erreurs'),('AUTOMATISER','Git + GitHub Actions\nTests et livraison du modèle')]):
    d.card(.55+i*4.14, 3.0, 3.92, 2.65, a, b, size=17)
s = d.text('Dépôt : https://github.com/samuelGabbai/P5_Futurisys', .65, 6.12, 12, .4, 18, TEAL, True)
s.text_frame.paragraphs[0].runs[0].hyperlink.address = 'https://github.com/samuelGabbai/P5_Futurisys'
d.finish()

new('Estimer le risque de départ d’un salarié', '02 / Contexte du modèle',
    'Classification binaire : Non vaut 0 et Oui vaut 1. Trois sources RH sont jointes par identifiant. Les 43 variables numériques sont préparées dans le notebook. L’API ne prend pas directement les CSV RH bruts. Une probabilité sert à l’analyse et ne constitue ni une cause de départ ni une décision RH automatisée.', 'docs/model.md • dataScientistTechNova.ipynb')
cards(('DONNÉES ET CIBLE','SIRH + sondage + évaluation\n1 470 salariés distincts\n237 départs : 16,12 %\nCible : a_quitte_l_entreprise'),('ENTRÉE ET SORTIE','43 variables préparées\nProbabilité de départ\nDécision selon le seuil\nArtefact : turnover_model.joblib'), 'Aide à l’analyse RH : les associations statistiques ne prouvent pas une causalité.')

new('Comparer les modèles et justifier le choix', '03 / Métriques et modèle final',
    'Comparaison historique sur les données d’entraînement, validation croisée stratifiée à cinq folds. La forêt optimisée est retenue pour les non-linéarités, la pondération des classes et une profondeur limitée. LightGBM a un F1 moyen supérieur : ne pas affirmer que la forêt est universellement meilleure. Les concurrents ne disposent pas tous d’une évaluation finale comparable sur le test.', 'docs/model.md • Notebook : cellules 31, 34, 54 et 55')
d.table(['Modèle / validation croisée','F1 moyen','ROC-AUC'],[
['Dummy stratifié','0,1644','0,5054'],['Régression logistique équilibrée','0,4968','0,8279'],['Random Forest initial','0,4189','0,8024'],['Random Forest optimisé — retenu','0,5048','Non reportée'],['LightGBM','0,5226','0,8030'],['Random Forest + SMOTE','0,4600','0,7689']],.55,1.85,[7.2,2.5,2.5],row_h=.53,font=16)
d.banner('Forêt finale : 300 arbres • profondeur 5 • classes équilibrées • calibration sigmoid',y=6.05)
d.finish()

new('Le seuil améliore la détection des départs', '04 / Résultats prédictifs',
    'Split stratifié : 1 176 lignes train et 294 test, dont 47 départs. Seuil 0,223181 choisi à partir des probabilités out-of-fold du train. Les chiffres présentés proviennent du notebook enregistré, pas d’un nouvel entraînement. Le rappel augmente, mais les fausses alertes aussi. L’accuracy naïve toujours resté est 84,01 %, d’où l’importance du rappel et du F1. Préparation ajustée avant split : limite de fuite d’information à corriger.', 'docs/model_metrics.json • Résultats historiques examinés le 27/10/2026')
d.table(['Métrique sur 294 salariés','Seuil 0,50','Seuil 0,2232'],[['Accuracy','81,63 %','80,27 %'],['Précision départ','34,78 %','42,03 %'],['Rappel départ','17,02 %','61,70 %'],['F1 départ','0,2286','0,5000'],['ROC-AUC','0,7692','0,7692']],.55,1.9,[6.2,3,3],row_h=.59,font=18)
d.banner('1 176 lignes train / 294 test • 47 départs dans le test • pas de validation externe',y=6.05)
d.finish()

new('L’API relie le client, la base et le modèle', '05 / API — introduction',
    'FastAPI expose un modèle chargé en mémoire. Chaque inférence enregistre les inputs, les relit, effectue le calcul puis valide et persiste les outputs avant réponse. X-Request-ID relie toutes les étapes. Une BDD indisponible bloque le calcul avec 503. Swagger documente les contrats et permet les essais.', 'api.py • inference.py • docs/architecture.md')
for i,(a,b) in enumerate([('CLIENT','JSON / CSV / ID'),('FASTAPI','Auth + Pydantic'),('POSTGRESQL','Inputs persistés'),('MODÈLE','Probabilité / classe')]):
    x=.55+i*3.15
    d.card(x,2.1,2.75,2.35,a,b,size=16)
    if i<3: d.arrow(x+2.78,3.25,x+3.1,3.25)
d.text('Résultat → validation → stockage et relecture → réponse au client',.7,4.95,12, .6,22,TEAL,True)
d.banner('Swagger : http://127.0.0.1:8000/docs • Traçabilité : en-tête X-Request-ID',y=6.05)
d.finish()

new('Neuf endpoints et des droits explicites', '06 / API — routes et rôles',
    'Les trois routes CSV sont regroupées sur une ligne. Utilisateur appelle les routes métier. Livreur télécharge ou publie le modèle, admin cumule les permissions. /predict et le score salarié utilisent le seuil optimisé. /predict/file utilise la décision native ; /score/file présente accuracy native et métriques au seuil. 401 signale un défaut d’authentification et 403 un droit insuffisant.', 'api.py • auth.py • docs/api.md')
d.table(['Méthode et route','Utilité','Accès'],[['GET /health','Disponibilité','Public'],['GET /auth/me','Identité et permissions','Compte actif'],['GET /features','Liste des 43 variables','Utilisateur'],['POST /predict','Prédiction JSON','Utilisateur'],['POST /predict/file, /predict-proba/file, /score/file','Classe, probabilité, métriques CSV','Utilisateur'],['GET /employees/{id}/score','Score du salarié stocké','Utilisateur'],['GET /model/download','ZIP modèle + métadonnées','Livreur']],.55,1.85,[6.15,3.65,2.4],row_h=.54,font=12.5)
d.banner('Admin cumule les droits • HTTP Basic • 401 : identité refusée / 403 : droit insuffisant',y=6.25)
d.finish()

new('Pydantic contrôle les entrées et les sorties', '07 / API — validation des données',
    'PredictionRequest vérifie les clés du modèle en contexte. NumericValue autorise les valeurs numériques et les chaînes numériques convertibles, mais refuse booléens, null et valeurs non finies. Les champs supplémentaires sont interdits. Les réponses sont aussi validées : probabilités bornées, classes binaires, longueurs cohérentes. Les rejets d’entrée sont des 422. Cette validation ne remplace pas la préparation métier ni un contrôle de dérive.', 'schemas.py • api.py • tests/')
cards(('AVANT LE CALCUL','43 noms de variables attendus\nAucune variable manquante / en trop\nNombres finis, sans null ni booléen\nRejet HTTP 422 si non conforme'),('APRÈS LE CALCUL','Probabilités entre 0 et 1\nClasses limitées à 0 et 1\nUne sortie par ligne d’entrée\nSomme des probabilités = 1'), 'Exemples rejetés : variable absente, valeur « texte », NaN ou cible autre que 0/1 et Non/Oui.')

new('La couverture mesure le code exécuté', '08 / Qualité — couverture de code',
    'Ces preuves datent de la recette du 4 novembre, elles ne sont pas un nouveau lancement des tests à la création de ce PPT. Périmètre : huit modules applicatifs et scripts opérationnels ; générateurs de présentations exclus. Le seuil de couverture configuré en CI est 95 %. Une forte couverture n’assure pas l’absence de défauts ; elle complète la pertinence des assertions.', 'docs/test_results.json • pyproject.toml • Recette du 04/11/2026')
d.stat(.65,2.0,3.6,str(tests['tests']),'tests réussis sur PostgreSQL')
d.stat(4.85,2.0,3.6,'97,88 %','couverture mesurée')
d.stat(9.05,2.0,3.6,'95 %','minimum requis en CI')
d.card(.55,4.05,5.95,2.3,'PÉRIMÈTRE','8 modules + scripts opérationnels\nGénérateurs de PPT exclus\n0 échec, 0 erreur, 0 test ignoré',size=16)
d.card(6.8,4.05,5.95,2.3,'RAPPORTS','JUnit : reports/junit.xml\nCouverture : XML, JSON et htmlcov/\nSynthèse : docs/test_results.json',size=16)
d.finish()

new('Tester les cas normaux et les échecs', '09 / Qualité — tests fonctionnels',
    'Le runner PostgreSQL crée une base temporaire puis la supprime. Il ne vide pas la base hrnova. La recette HTTP réelle vérifie les rôles et cinq routes d’inférence. Le benchmark a mesuré 48 requêtes sans erreur ; ce petit échantillon n’est pas un SLA. Le build et le smoke Docker sont configurés en CI mais ne sont pas prouvés par le rapport local.', 'tests/ • scripts/run_postgres_tests.py • docs/performance_results.json')
cards(('TESTS UNITAIRES','Validation des données et sorties\nPermissions utilisateur / livreur\nContraintes, doublons et rollback\nLimites CSV et échecs du modèle'),('TESTS FONCTIONNELS','PostgreSQL temporaire isolé\nAppels API et persistance réelle\n401 / 403 selon les comptes\n48 appels mesurés : 0 erreur'), 'Commande : uv run --no-sync python scripts/run_postgres_tests.py')

new('BDD : schéma relationnel et cardinalités', '10 / BDD — modèle de données',
    'Schéma UML simplifié, équivalent relationnel : PK est la clé primaire, FK une référence et UK une unicité. Pour les tables sources, un salarié possède au plus un sondage et une évaluation ; l’import complet vérifie leur présence. prepared_employees porte une clé composée salarié/version. Un échange peut ne pas avoir de version, par exemple lors d’un rejet précoce. Un input peut ne pas référencer un salarié, notamment pour un fichier externe. Une sortie est un document JSONB par échange, pouvant contenir plusieurs prédictions.', 'database.py • docs/database.md • docs/schema.sql')
# Deux ensembles de relations, avec cardinalités explicites sur chaque lien.
def node(x,y,w,title,body):
    d.box(x,y,w,1.15,WHITE,rounded=True)
    d.text(title,x+.12,y+.1,w-.24,.3,15,TEAL,True)
    d.text(body,x+.12,y+.48,w-.24,.6,11,INK)
def edge(x1,y1,x2,y2,label,tx,ty,tw):
    d.arrow(x1,y1,x2,y2)
    d.text(label,tx,ty,tw,.28,10,TEAL)
node(.55,1.9,3.1,'surveys','PK / FK employee_id\nUK code_sondage')
node(5.0,1.9,3.1,'employees','PK id_employee\nâge, revenu, poste…')
node(9.65,1.9,3.1,'evaluations','PK / FK employee_id\nUK eval_number')
edge(5,2.45,3.65,2.45,'1 → 0..1',3.7,2.1,1.25)
edge(8.1,2.45,9.65,2.45,'1 → 0..1',8.3,2.1,1.3)
node(.55,3.7,3.1,'model_versions','PK sha256\nseuil, features JSONB')
node(5,3.7,3.1,'prepared_employees','PK / FK (employee_id, model_sha256)\nfeatures JSONB')
edge(3.65,4.2,5,4.2,'1 → 0..N',3.7,3.85,1.25)
edge(6.55,3.05,6.55,3.7,'1 → 0..N',6.7,3.25,1.3)
node(.55,5.5,3.1,'api_exchanges','PK id ; FK model_sha256 (nullable)\nroute, statut, durée, identité')
node(5,5.5,3.1,'model_inputs','PK id ; FK exchange_id, employee_id\nUK (exchange_id, row_index)')
node(9.65,5.5,3.1,'model_outputs','PK / FK exchange_id\npayload JSONB, date')
edge(2.1,4.85,2.1,5.5,'0..1 → 0..N',2.25,5.02,2)
edge(3.65,6.05,5,6.05,'1 → 0..N',3.7,5.7,1.25)
d.text('Échange 1 → 0..1 sortie',9.65,5.1,3.1,.3,12,TEAL)
d.text('Salarié 0..1 → 0..N inputs',9.15,3.65,3.6,.35,12,TEAL)
d.finish()

new('Stocker, tracer et préparer l’analyse', '11 / BDD — données et volumes',
    'Chaque source contient 1 470 lignes ; ce ne sont pas 4 410 salariés distincts. L’import est transactionnel et met à jour les lignes existantes. Les dates, routes et statuts sont indexés. Le contrat accepte au maximum 10 MiB et 10 000 lignes CSV ; les 128 colonnes constituent une garde de parseur, pas le contrat métier. Les vues agrégées répondent aux besoins analytiques mais aucun tableau de bord graphique n’est livré.', 'create_db.py • database.py • docs/analytics.md • docs/performance.md')
cards(('STOCKAGE ET INTÉGRITÉ','3 sources × 1 470 lignes\n1 470 profils préparés / version\nPK, FK, unicité et transactions\nJSONB pour features et résultats'),('VOLUMES ET ANALYTIQUE','Index sur dates, routes et statuts\nCSV : 10 MiB / 10 000 lignes max.\nVues : activité, erreurs, scores\nScores agrégés par groupes ≥ 5'), 'À industrialiser : rétention, sauvegarde/restauration, charge prolongée et tableau de bord.')

new('PostgreSQL local et cible de déploiement', '12 / BDD — installation et simulation distante',
    'Le script local configure une instance dédiée sur 5433, importe les sources et sépare administrateur et rôle applicatif. La cible distante dessinée est une simulation d’architecture, pas un service publié. deployment/compose.yml contient le service API, pas PostgreSQL. Il faut un serveur de base séparé, des connexions sécurisées, une initialisation contrôlée et une recette de restauration avant exploitation.', 'scripts/local_postgres.py • deployment/compose.yml • docs/deployment.md')
d.card(.55,1.95,5.95,3.1,'LOCAL VÉRIFIÉ','PostgreSQL 18 • 127.0.0.1:5433\nBase : hrnova • schéma : public\nAPI : hrnova_app, droits limités\nInitialisation + import par script',size=18)
d.card(6.8,1.95,5.95,3.1,'DISTANT — SIMULATION','Client → HTTPS → API conteneurisée\nAPI → PostgreSQL privé\nDATABASE_URL injectée au déploiement\nSauvegardes et supervision à prévoir',size=18)
d.box(.55,5.4,12.2,.85,NAVY,rounded=True)
d.text('uv run --no-sync python scripts/local_postgres.py start',.75,5.63,11.8,.4,19,WHITE)
d.finish()

new('Git conserve et explique chaque évolution', '13 / Versionnement',
    'Git versionne les sources, la configuration, la documentation et l’artefact de référence. GitHub héberge le dépôt et la revue. Une branche isole une évolution, un commit décrit une unité cohérente, une pull request organise la revue. Les conventions sont documentées ; cette présentation ne certifie pas la qualité de tous les anciens commits. Le lien est cliquable.', 'CONTRIBUTING.md • .gitignore • .github/pull_request_template.md')
cards(('POURQUOI GIT ?','Historique et comparaison des versions\nRetour à un état identifié\nCollaboration et revue des changements\nCommit relié au modèle livré'),('PROCESSUS DU PROJET','Branche de travail → commits explicites\nPull request → tests automatiques\nFusion → validation / livraison\n.env et données locales exclus de Git'), 'Dépôt : github.com/samuelGabbai/P5_Futurisys')
# Hyperlien également sur le bandeau du dépôt.
for sh in d.slide.shapes:
    if sh.has_text_frame and sh.text.startswith('Dépôt :'):
        sh.text_frame.paragraphs[0].runs[0].hyperlink.address='https://github.com/samuelGabbai/P5_Futurisys'

new('Une arborescence organisée par responsabilité', '14 / Architecture du dépôt',
    'Le code applicatif reste à la racine et les responsabilités sont séparées en modules. Les scripts assurent les opérations ; les tests et la documentation ont leurs répertoires. pyproject.toml et uv.lock servent d’équivalent au requirements.txt. .local et .env sont propres à la machine et ignorés par Git.', 'Arborescence du dépôt • docs/architecture.md')
d.box(.55,1.85,7.15,4.65,NAVY,rounded=True)
d.text("P5_Futurisys/\n├── api.py · schemas.py · auth.py\n├── inference.py · audit.py · model_release.py\n├── database.py · create_db.py\n├── Data/ · artifacts/ · migrations/\n├── tests/ · scripts/\n├── docs/ · presentations/\n├── .github/workflows/ci.yml\n├── deployment/compose.yml · Dockerfile\n└── pyproject.toml · uv.lock",.78,2.08,6.7,4.15,18,WHITE)
d.card(8.0,1.85,4.75,4.65,'RESPONSABILITÉS','Racine : service applicatif\nData / artifacts : sources et modèle\ntests / scripts : qualité et opérations\ndocs : documentation MkDocs\n.github / deployment : automatisation',size=18)
d.finish()

new('GitHub Actions automatise les contrôles', '15 / Pipeline CI/CD',
    'Le YAML installe les dépendances verrouillées, teste avec PostgreSQL 18 et produit les rapports, le package et MkDocs. Il construit et teste l’image Docker puis prépare l’export. Les environnements sont associés aux branches : main production, develop staging, autres development, avec base de test isolée. Le déploiement API est conditionné à ENABLE_API_DEPLOYMENT et à un runner configuré. Aucun succès distant n’est attesté par les seules preuves locales.', '.github/workflows/ci.yml • scripts/smoke_container.py • docs/deployment.md')
for i,(a,b) in enumerate([('1. TESTER','Pytest + PostgreSQL\nCouverture ≥ 95 %'),('2. CONSTRUIRE','Package + MkDocs\nImage Docker + smoke'),('3. LIVRER','Export modèle validé\nDéploiement conditionnel')]):
    d.card(.55+i*4.14,2,3.92,2.75,a,b,size=18)
d.text('development  →  staging (develop)  →  production (main)',.7,5.1,12,.5,23,TEAL,True)
d.banner('Pipeline configuré ; exécution GitHub et build Docker distant restent à confirmer.',y=6.05)
d.finish()

new('Gérer les secrets et limiter les droits', '16 / Sécurité',
    'Les mots de passe applicatifs sont hachés avec PBKDF2-SHA256, sel aléatoire et 600 000 itérations. La base dispose d’un rôle de service distinct de l’administrateur. Les fichiers locaux sont protégés et ignorés. GitHub injecte les secrets des environnements. Ne jamais projeter les valeurs ; HTTPS, rotation et limitation de tentatives restent nécessaires pour l’exposition distante.', 'auth.py • docs/authentication.md • docs/deployment.md')
cards(('EN LOCAL','DATABASE_URL dans .env\nComptes : HRNOVA_AUTH_USERS\nHachage PBKDF2-SHA256\nFichiers sensibles protégés (0600)'),('EN CI / PRODUCTION','Secrets GitHub par environnement\nHF_TOKEN limité à la publication\nIdentité livreur + mot de passe\nAucun secret en clair dans le PPT'), 'Utilisateur : API métier • Livreur : livraison • Admin : les deux • HTTPS pour un accès distant')

new('Hugging Face : publier le modèle validé', '17 / Livraison en ligne du modèle',
    'La cible configurée est le dépôt Model SamGabb/hrnova. Le workflow publie sur main après validation, à condition que le dépôt, les secrets et le compte livreur ou admin soient disponibles. Le ZIP et la publication excluent records_by_employee_id. Publier un artefact sur un dépôt Model ne lance pas une API en ligne et ne réentraîne pas le modèle. La disponibilité du dépôt et une publication réussie ne sont pas vérifiées pour cette présentation.', 'model_release.py • scripts/publish_huggingface.py • docs/huggingface.md')
cards(('EXPORT CONTRÔLÉ','turnover_model.joblib\nmetadata.json : hash et commit\nrequirements.txt + fiche modèle\nDictionnaire des salariés exclu'),('PUBLICATION CONFIGURÉE','Cible : huggingface.co/SamGabb/hrnova\nCompte livreur/admin + HF_TOKEN\nExport du commit validé en CI\nPublication effective à vérifier'), 'Dépôt Model = distribution de l’artefact ; une API en ligne nécessite un déploiement séparé.')

new('Résumé : du modèle au service traçable', '18 / Bilan des actions',
    'Distinguer les éléments construits et les preuves datées. Le modèle est existant et exposé, la traçabilité et les contrôles d’accès sont implémentés, la recette locale est documentée. Les configurations de déploiement existent mais ne prouvent pas un environnement distant opérationnel.', 'docs/validation.md • docs/test_results.json • README.md')
d.table(['Action','Résultat / état'],[['Exposer le modèle','9 endpoints FastAPI + Swagger + validation Pydantic'],['Sécuriser les usages','Rôles utilisateur, livreur, admin et droits SQL limités'],['Tracer les interactions','Sources, versions, inputs, outputs et erreurs en PostgreSQL'],['Vérifier le fonctionnement','239 tests réussis ; couverture 97,88 % au 04/11/2026'],['Mesurer et documenter','Benchmark, vues analytiques et documentation MkDocs'],['Préparer la livraison','YAML, Docker et export HF configurés ; distant à valider']],.55,1.95,[4.15,8.05],row_h=.63,font=16)
d.finish()

new('Améliorations : fiabilité puis industrialisation', '19 / Perspectives',
    'Priorité modèle : inclure tout le preprocessing dans une pipeline ajustée uniquement sur le train, puis refaire la comparaison et une validation temporelle avec intervalles de confiance. Vérifier les disparités entre populations avant une utilisation RH. Priorité exploitation : preuve CI distante, TLS, rotation, restauration, tests de charge réalistes et supervision. Un tableau de bord agrégé peut exploiter les vues existantes.', 'docs/model.md • docs/maintenance.md • docs/analytics.md • docs/performance.md')
cards(('MODÈLE ET DONNÉES','Pipeline de préparation sérialisable\nCorriger la préparation avant split\nValidation temporelle et incertitude\nAnalyse des erreurs par population'),('EXPLOITATION DU SERVICE','Valider CI et déploiement distant\nHTTPS, rotation et limitation d’accès\nSauvegardes + tests de restauration\nCharge, dérive et tableau de bord'), 'Prochaine étape : prouver une livraison reproductible de bout en bout sur la cible retenue.')

assert len(d.prs.slides) == 19
OUT.mkdir(exist_ok=True)
d.prs.save(OUT / f'{STEM}.pptx')
preview=OUT / 'apercus_plan_2026-11-10'
preview.mkdir(exist_ok=True)
overview=Image.new('RGB',(1600,1125),'white')
for i,img in enumerate(d.images):
    img.save(preview / f'slide_{i+1:02d}.png')
    overview.paste(img.resize((400,225)),((i%4)*400,(i//4)*225))
overview.save(OUT / f'{STEM}_Apercu.png')
notes=['# HRNova — Notes orateur', '', '19 diapositives selon le plan demandé. Preuves techniques datées ; aucune publication distante attestée.', '']
for i,(title,note,source) in enumerate(d.notes,1):
    notes += [f'## {i:02d} — {title}', '', note, '', f'Sources : {source}', '']
(OUT / f'{STEM}_Notes.md').write_text('\n'.join(notes))
print(f'Créé : {STEM}.pptx — 19 diapositives avec notes et aperçus')
