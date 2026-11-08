"""Actualiser une copie de la soutenance en conservant les diapositives non remplacées.

PYTHONPATH=/private/tmp/hrnova-slides-deps .venv/bin/python scripts/build_updated_presentation.py
"""
from copy import deepcopy
from datetime import datetime
import argparse
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Inches

from build_presentation import Deck, ROOT, BG, INK, LIME, MUTED, NAVY, PPI, TEAL, WHITE, font_file

OUT = ROOT / "presentations"
STEM = "HRNova_Soutenance_Actualisee_2026-11-04"


def code(d, text, x=.55, y=2.0, w=12.2, h=1.7, size=18):
    d.box(x, y, w, h, NAVY, rounded=True)
    d.text(text, x+.22, y+.22, w-.44, h-.44, size, WHITE)


def notes_frame(slide, reference=None):
    frame = slide.notes_slide.notes_text_frame
    if frame is None and reference is not None:
        for shape in reference.notes_slide.shapes:
            if shape.is_placeholder and shape._element.xpath('.//p:ph[@type="body"]'):
                slide.notes_slide.shapes._spTree.insert_element_before(deepcopy(shape._element), "p:extLst")
                break
        frame = slide.notes_slide.notes_text_frame
    if frame is None:
        raise ValueError("La zone de notes du support source est absente.")
    return frame


def build(source, output_dir):
    prs = Presentation(source)
    tests = json.loads((ROOT / "docs/test_results.json").read_text())
    performance = json.loads((ROOT / "docs/performance_results.json").read_text())
    assert tests["failures"] == tests["errors"] == tests["skipped"] == 0
    total = len(prs.slides) + 6
    d = Deck(total=total)
    replacements, additions = {}, {}
    def register(key, replace=True):
        (replacements if replace else additions)[key] = len(d.prs.slides)-1
        d.finish()

    d.new("Du modèle à une API sécurisée et traçable", "HRNova / TechNova Partners",
          "Le projet relie un modèle calibré à une API locale validée, une base PostgreSQL et une chaîne CI/CD. L’état technique est actualisé au 4 novembre 2026. Les performances prédictives restent celles du notebook évalué en octobre et sont distinctes des mesures HTTP récentes. Le déploiement local répond au référentiel ; le build Docker réel reste à confirmer sur GitHub Actions.",
          "État technique : 4 novembre 2026 • Métriques ML historiques : octobre 2026", dark=True)
    d.text("Estimer une probabilité.\nContrôler les accès.\nRetrouver chaque échange.", .65, 2.1, 11.9, 2.15, 30, WHITE, bold=True)
    d.stat(.65,5.1,3.6,"1 470","salariés",True)
    d.stat(4.85,5.1,3.6,"43","variables préparées",True)
    d.stat(9.05,5.1,3.6,"9","endpoints documentés",True)
    register("cover")

    d.new("Neuf routes, des accès selon le rôle", "API / Contrat et permissions",
          "Distinguer les cinq routes d’inférence, les routes de contrat et d’identité, et la livraison du modèle. /health reste public. Les comptes utilisateur et admin accèdent aux API métier, tandis que livreur et admin peuvent télécharger le modèle. Les anciens rôles lecteur et analyste restent compatibles avec leurs permissions plus limitées. Les trois routes CSV partagent les contrôles de format et la traçabilité.",
          "Sources : api.py • auth.py • docs/openapi.json")
    d.table(["Route", "Usage", "Rôle principal"],[
        ["GET /health", "Disponibilité du service", "Public"],
        ["GET /auth/me", "Identité et permissions", "Compte actif"],
        ["GET /features", "Contrat des 43 variables", "Utilisateur"],
        ["POST /predict", "Prédiction JSON au seuil", "Utilisateur"],
        ["POST /predict/file, /predict-proba/file, /score/file", "Inférence et score CSV", "Utilisateur"],
        ["GET /employees/{id}/score", "Profil préparé lu en BDD", "Utilisateur"],
        ["GET /model/download", "Modèle et métadonnées ZIP", "Livreur"],
    ],.55,1.85,[6.1,3.7,2.4],row_h=.53,font=13)
    d.banner("Admin cumule les droits ; les trois routes CSV sont regroupées sur une ligne.", y=6.25)
    register("api")

    d.new("Deux droits distincts : utiliser et livrer", "Sécurité / Authentification et rôles",
          "Le contrôle d’accès est appliqué par dépendance FastAPI. Le rôle utilisateur autorise les API métier, notamment le score par identifiant salarié ; il ne permet pas de télécharger ni publier le modèle. Le rôle livreur possède uniquement le droit de livraison. Admin cumule les deux. HTTP Basic vérifie le mot de passe haché à chaque appel. Un compte absent ou désactivé est refusé ; un mauvais rôle produit 403. Le token Hugging Face reste nécessaire en plus du droit applicatif pour publier.",
          "Sources : auth.py • docs/authentication.md")
    d.table(["Rôle", "API métier", "Télécharger", "Publier le modèle"],[
        ["utilisateur", "Oui", "Non", "Non"],
        ["livreur", "Non", "Oui", "Oui + token HF"],
        ["admin", "Oui", "Oui", "Oui + token HF"],
    ],.55,2.0,[3.0,2.8,2.8,3.6],row_h=.68,font=17)
    d.text("PBKDF2-SHA256 • sel aléatoire • 600 000 itérations",.7,5.0,11.9,.45,20,TEAL,bold=True)
    d.banner("HTTP Basic pour l’usage local ; HTTPS et limitation des tentatives avant une exposition distante.")
    register("roles",False)

    d.new("Se connecter comme utilisateur simple", "Démonstration / Lancement et connexion",
          "PostgreSQL doit être démarré avant l’API. La commande Uvicorn est commune à tous les rôles : le rôle dépend du compte qui s’authentifie, pas d’une option de lancement. Dans Swagger, utiliser Authorize avec application. Le secret aléatoire est disponible uniquement dans le fichier local protégé, sans l’afficher pendant la soutenance. Le script bootstrap crée les comptes une fois et préserve une configuration existante. /auth/me permet de vérifier que le rôle effectif est utilisateur.",
          "Sources : scripts/manage_users.py • docs/installation.md • docs/authentication.md")
    code(d,"uv run --no-sync python scripts/local_postgres.py start\nuv run --no-sync uvicorn api:app \\\n  --host 127.0.0.1 --port 8000 --reload",h=1.65,size=18)
    d.card(.55,4.0,5.95,2.3,"DANS SWAGGER","127.0.0.1:8000/docs → Authorize\nCompte : application\nVérifier le rôle avec GET /auth/me",size=16)
    d.card(6.8,4.0,5.95,2.3,"IDENTIFIANTS LOCAUX",".local/api-credentials.env\nValeur : HRNOVA_VERIFY_PASSWORD\nFichier protégé ; aucun secret projeté.",size=16)
    register("login",False)

    d.new("Livrer un modèle sans exporter les lignes RH", "Livraison / Téléchargement et publication",
          "L’archive de livraison utilise une liste de clés autorisées : modèle, seuil, variables et classe positive. Les autres champs, dont records_by_employee_id, sont exclus. Elle comporte aussi les hashes et les versions de bibliothèques. Le même export est utilisé pour le téléchargement et Hugging Face. Le script de publication vérifie un compte livreur ou admin avant tout appel distant, puis utilise un token HF autorisé en écriture. Publier n’entraîne pas le modèle et ne déploie pas l’API. L’exclusion des lignes source ne garantit pas à elle seule l’anonymisation du modèle appris.",
          "Sources : model_release.py • scripts/publish_huggingface.py • docs/huggingface.md")
    code(d,"curl --fail -u livraison \\\n  http://127.0.0.1:8000/model/download \\\n  --output hrnova-model.zip",h=1.6,size=18)
    d.card(.55,4.0,5.95,2.3,"ARCHIVE ZIP","turnover_model.joblib • metadata.json\nrequirements.txt • README.md\nSans dictionnaire individuel des salariés.",size=16)
    d.card(6.8,4.0,5.95,2.3,"PUBLICATION CONTRÔLÉE","Compte livreur/admin + token HF\nExport du commit validé, hash vérifié\nSecrets injectés par l’environnement.",size=16)
    register("delivery",False)

    d.new("Une recette complète sur PostgreSQL", "Qualité / Tests unitaires et fonctionnels",
          f"La recette finale exécute {tests['tests']} tests sur PostgreSQL dans une base temporaire qui est supprimée à la fin, sans vider hrnova. Aucun test n’est ignoré. La couverture de {tests['coverage_percent']:.2f} % porte sur les huit modules applicatifs et les scripts opérationnels ; les générateurs de présentations sont exclus. Le seuil CI est 95 %. Les tests couvrent les erreurs, transactions, authentification, volumes et vues analytiques. Le rapport BDD réel valide les cinq routes, les 1 470 lignes par source et les privilèges SQL limités. La couverture ne remplace pas un vrai test de déploiement Docker.",
          "Sources : docs/test_results.json • docs/database_validation.json • docs/validation.md")
    d.stat(.65,2.05,3.6,str(tests['tests']),"tests PostgreSQL réussis")
    d.stat(4.85,2.05,3.6,f"{tests['coverage_percent']:.2f} %".replace('.',','),"couverture du périmètre élargi")
    d.stat(9.05,2.05,3.6,"0","échec et test ignoré")
    d.card(.55,4.1,5.95,2.25,"CAS CRITIQUES","401/403, données invalides, rollback,\nFK et doublons, échec du modèle,\nlimites CSV et agrégats analytiques.",size=16)
    d.card(6.8,4.1,5.95,2.25,"PREUVES CONSERVÉES","JUnit, XML/HTML/JSON de couverture\nRapport des cinq routes authentifiées\nBase de tests isolée et jetable.",size=16)
    register("tests")

    d.new("Du push aux contrôles avant livraison", "CI/CD / Validation et déploiement",
          "Le job principal installe les dépendances verrouillées, lance les tests PostgreSQL, construit le package et la documentation, puis initialise la base du contrôle Docker. Il crée des comptes temporaires, construit réellement l’image et teste ses routes HTTP et permissions. Ce contrôle est prévu aussi pour les pull requests. Le contexte Docker a été corrigé pour inclure auth.py et model_release.py. Docker étant absent de la machine locale, le vrai build doit être confirmé par la prochaine exécution GitHub Actions. La publication et le déploiement restent conditionnés aux environnements, secrets et runners configurés.",
          "Sources : .github/workflows/ci.yml • .dockerignore • scripts/smoke_container.py")
    for i,(title,body) in enumerate([
        ("1. VALIDER","Tests PostgreSQL\nContrats et rôles\nCouverture ≥ 95 %"),
        ("2. CONSTRUIRE","Package et MkDocs\nImage Docker\nSources complètes"),
        ("3. CONTRÔLER","HTTP + PostgreSQL\nPrédiction réelle\nRefus 401 / 403"),
        ("4. LIVRER","Modèle : droit + HF\nAPI : cible préparée\nSecrets et validations"),
    ]):
        x=.55+i*3.1
        d.card(x,2.1,2.9,3.0,title,body,size=16)
        if i<3:d.arrow(x+2.94,3.6,x+3.06,3.6)
    d.banner("Local : tests et HTTP vérifiés. Docker réel : à confirmer dans GitHub Actions.",y=5.8)
    register("ci")

    d.new("Mesurer la latence et le débit du service", "Exploitation / Benchmark HTTP réel",
          "Le benchmark utilise le modèle réel, HTTP Basic et PostgreSQL, y compris les transactions de traçabilité. Chaque scénario comporte un préchauffage exclu et huit appels mesurés, soit 48 requêtes sans erreur. La machine est un Mac ARM64 de dix CPU avec un processus Uvicorn. La concurrence augmente le débit et la latence ; le p95 sur huit observations reste une estimation indicative, pas un SLA ni un test d’endurance. Les valeurs présentées proviennent du JSON de mesure et sont distinctes des métriques prédictives historiques.",
          "Source : docs/performance_results.json • macOS ARM64, 10 CPU • 8 requêtes par scénario")
    rows=[]
    for s in performance['scenarios']:
        label='JSON : 1 profil' if s['route']=='/predict' else f"CSV : {s['rows_per_request']:,} lignes".replace(',',' ')
        rows.append([label,str(s['concurrency']),f"{s['latency_ms']['p95']:.0f} ms",f"{s['requests_per_second']:.2f}",str(s['errors'])])
    d.table(["Requête", "Parallèle", "p95 HTTP", "Requêtes/s", "Erreurs"],rows,.55,1.9,[4.2,1.8,2.1,2.1,2.0],row_h=.52,font=15)
    d.text("CSV : 10 Mio et 10 000 lignes maximum ; rejet avant inférence en cas de dépassement.",.7,5.9,11.9,.7,17,TEAL,bold=True)
    register("performance",False)

    d.new("Des besoins BI définis et deux vues SQL", "Analyse / Exploitation et tableaux de bord",
          "Le référentiel demande de décrire les besoins analytiques. Le projet définit les utilisateurs, décisions, KPI, sources, fréquences et droits, et fournit deux vues SQL sans prétendre qu’une interface de dashboard est hébergée. La vue technique agrège activité, statuts, latence et volumes. La vue métier agrège les scores unitaires par date, hash et seuil, en masquant les groupes de moins de cinq requêtes. Une requête n’est pas un salarié unique ; la fréquence des alertes n’est pas le turnover réel. Le compte SQL du service ne doit pas être distribué aux utilisateurs BI : un rôle dédié doit être provisionné avec seulement SELECT sur les vues nécessaires.",
          "Sources : docs/analytics.md • docs/migrations/003_analytics_views.sql")
    d.card(.55,2.0,5.95,3.4,"EXPLOITATION","analytics_daily_activity\n\nRequêtes, lignes, 401/403, échecs\nDurée moyenne et p95 par route\nLecture toutes les 5 minutes",size=17)
    d.card(6.8,2.0,5.95,3.4,"ANALYSE DES SCORES","analytics_model_scores\n\nAgrégats par jour, version et seuil\nGroupes d’au moins 5 requêtes\nAucun input ou identifiant RH exposé",size=17)
    d.banner("Une requête n’est pas un salarié unique ; un taux d’alertes n’est pas un taux de turnover.")
    register("analytics",False)

    d.new("Trois cibles, des secrets et un retour arrière", "Environnements / Service local et cible finale",
          "La cible démontrée est locale, ce qui est accepté par le référentiel actualisé. development, staging et production séparent configurations, bases et secrets. Le test est fourni par un job PostgreSQL isolé et une base jetable locale. La mise en service Docker est conditionnée à ENABLE_API_DEPLOYMENT=true et à des runners préparés. Le précontrôle vérifie la base et le modèle, une prédiction authentifiée suit le démarrage et un échec tente de restaurer l’image précédente. Les réglages de protection de branches et d’approbation GitHub doivent être configurés dans le service ; le YAML ne les active pas automatiquement.",
          "Sources : deployment/ • scripts/deploy_api.py • docs/deployment.md")
    d.table(["Branche / contexte", "Cible", "Port local de référence"],[
        ["development", "Développement", "8000"],
        ["develop", "Staging", "8002"],
        ["main", "Production", "8003"],
        ["Job de tests", "PostgreSQL isolé", "Base jetable"],
    ],.55,1.9,[4.5,3.8,3.9],row_h=.62,font=17)
    d.text("Secrets : DATABASE_URL, HRNOVA_AUTH_USERS et identifiants du contrôle HTTP.",.7,5.3,11.9,.65,17,TEAL,bold=True)
    d.banner("Cloud facultatif ; mise en service distante conditionnée à la préparation des cibles.",y=6.15)
    register("environments",False)

    d.new("Git : des changements lisibles et vérifiables", "Git / Conventions et revue",
          "Le nettoyage retire du suivi neuf artefacts générés tout en conservant leurs fichiers locaux : .DS_Store, bytecode, métadonnées egg-info et couverture. .editorconfig et CONTRIBUTING définissent la structure et les conventions. Les prochains commits décrivent le problème, le changement et la validation ; l’historique existant n’est pas réécrit. Le modèle de pull request demande les tests, les secrets ou migrations concernés sans leurs valeurs et le retour arrière éventuel. Les changements actuels doivent ensuite être committés et poussés pour déclencher la CI distante.",
          "Sources : CONTRIBUTING.md • .editorconfig • .github/pull_request_template.md")
    code(d,'git switch -c fix/validation-auth\ngit add scripts/verify_database.py tests/\ngit commit -m "fix(auth): authentifier la validation BDD"\ngit push -u origin fix/validation-auth',h=2.0,size=18)
    d.card(.55,4.35,5.95,2.0,"UN COMMIT EXPLICITE","Expliquer le déclencheur, la correction\net les vérifications dans le message.",size=16)
    d.card(6.8,4.35,5.95,2.0,"DES SORTIES NON VERSIONNÉES","Caches, secrets et rapports temporaires\nrestent hors des nouveaux suivis Git.",size=16)
    register("git")

    d.new("GitHub Actions : ce qui est réellement automatisé", "Git / Jobs et contrôles",
          "Les événements push, pull_request et merge_group déclenchent la validation. Les étapes d’un job s’enchaînent ; needs impose les dépendances entre jobs. Le contrôle principal comprend désormais Docker et un smoke HTTP avec PostgreSQL. Les jobs de publication du modèle et de déploiement API sont distincts. La protection des branches et les approbations sont des réglages GitHub à activer ; la présence du YAML ne prouve pas leur activation. Ne pas annoncer le build Docker comme exécuté localement puisqu’il doit être confirmé dans GitHub Actions.",
          "Source : .github/workflows/ci.yml • docs/validation.md")
    d.card(.55,2.1,3.93,3.1,"DÉCLENCHER","Push / pull request\nMachine runner\nDépendances verrouillées",size=18)
    d.card(4.65,2.1,3.93,3.1,"VÉRIFIER","Tests + couverture\nPackage + documentation\nDocker + contrôles HTTP",size=18)
    d.card(8.75,2.1,3.99,3.1,"AUTORISER","Environnement et secrets\nRôle de livraison + token HF\nCible API et runners prêts",size=18)
    d.banner("Un workflow présent doit encore être exécuté ; un push ne réentraîne pas automatiquement le modèle.",y=5.8)
    register("actions")

    d.new("Des acquis vérifiés et des limites explicites", "Regard critique / Prochaines étapes",
          "La préparation sans fuite et la validation indépendante restent les priorités du modèle. Les limites de prétraitement historique ne sont pas corrigées par les tests logiciels. L’authentification et les rôles sont désormais présents pour l’usage local. Une exposition distante exige HTTPS, limitation des tentatives, supervision et habilitations adaptées. Les mesures actuelles ne sont pas une garantie de capacité maximale. Les besoins analytiques sont formalisés ; une connexion BI avec rôle SQL dédié reste à provisionner selon le SI cible.",
          "Sources : docs/model.md • docs/performance.md • docs/analytics.md • docs/validation.md")
    for i,(title,body) in enumerate([
        ("Préparation sans fuite","Ajuster les transformations dans les folds ; exporter une pipeline complète."),
        ("Validation indépendante","Évaluer sur des données nouvelles ; préciser l’incertitude et les disparités."),
        ("Exploitation distante","Compléter les rôles existants par HTTPS, supervision et limitation des tentatives."),
        ("Capacité et gouvernance","Confirmer Docker en CI ; définir conservation, habilitations BI et charge cible."),
    ]):
        y=1.95+i*1.08
        d.text(f"{i+1:02d}",.68,y,.67,.55,26,TEAL,bold=True)
        d.text(title,1.65,y,10.8,.4,20,INK,bold=True)
        d.text(body,1.65,y+.46,10.8,.49,17,MUTED)
    register("limits")

    # Les identifiants de remplacement suivent le support réellement édité (28 slides).
    mapping={0:'cover',13:'api',19:'tests',20:'ci',22:'git',24:'actions',26:'limits'}
    assert len(prs.slides)==28, "Le support source a changé : contrôler la correspondance des diapositives."
    originals=list(prs.slides)
    old_ids=list(prs.slides._sldIdLst)
    generated={}
    def append_generated(key):
        index=(replacements if key in replacements else additions)[key]
        src=d.prs.slides[index]
        dest=prs.slides.add_slide(prs.slide_layouts[6])
        for shape in list(dest.shapes):
            dest.shapes._spTree.remove(shape._element)
        for shape in src.shapes:
            dest.shapes._spTree.insert_element_before(deepcopy(shape._element),'p:extLst')
        dest.background.fill.solid()
        dest.background.fill.fore_color.rgb=src.background.fill.fore_color.rgb
        notes_frame(dest,src).text=src.notes_slide.notes_text_frame.text
        generated[key]=(dest,list(prs.slides._sldIdLst)[-1],d.images[index])
    for key in [*mapping.values(),*additions]:
        append_generated(key)
    order=[]
    for i,item in enumerate(old_ids):
        order.append(generated[mapping[i]][1] if i in mapping else item)
        if i==9:order.append(generated['analytics'][1])
        if i==13:
            order.extend(generated[k][1] for k in ('roles','login','delivery'))
        if i==19:order.append(generated['performance'][1])
        if i==20:order.append(generated['environments'][1])
    for item in list(prs.slides._sldIdLst):prs.slides._sldIdLst.remove(item)
    for item in order:prs.slides._sldIdLst.append(item)
    # Retirer les anciennes parties remplacées du paquet final, sans toucher les autres slides.
    for i in mapping:prs.part.drop_rel(old_ids[i].rId)
    assert len(prs.slides)==total
    all_notes=[]
    updated_previews=[]
    for number,slide in enumerate(prs.slides,1):
        for shape in slide.shapes:
            if shape.has_text_frame and re.fullmatch(r'\d+\s*/\s*\d+',shape.text.strip()):
                runs=[r for p in shape.text_frame.paragraphs for r in p.runs]
                if runs:
                    runs[0].text=f'{number:02d} / {total:02d}'
                    for run in runs[1:]:run.text=''
        texts=[shape.text for shape in slide.shapes if shape.has_text_frame and shape.text.strip()]
        title=texts[1] if len(texts)>1 else texts[0]
        note=notes_frame(slide).text
        note=note.replace('sept endpoints','neuf endpoints').replace('sans authentification HTTP','avec authentification HTTP Basic et rôles')
        if slide is originals[25]:
            note='La documentation inclut maintenant l’authentification, les besoins analytiques, les performances et les preuves de recette. Swagger permet de tester le rôle utilisateur et les guides distinguent les résultats vérifiés localement des contrôles Docker à confirmer dans GitHub Actions.'
        notes_frame(slide).text=note
        all_notes.extend([f'## {number:02d} — {title}','',note,''])
        for key,(generated_slide,_,preview) in generated.items():
            if slide is generated_slide:
                image=preview.copy()
                draw=ImageDraw.Draw(image)
                fill=NAVY if key=='cover' else BG
                draw.rectangle((1380,842,1550,884),fill='#'+fill)
                font=ImageFont.truetype(font_file(),17)
                draw.text((1398,847),f'{number:02d} / {total:02d}',font=font,fill='#'+('BDD1D6' if key=='cover' else MUTED))
                updated_previews.append((number,image))
    prs.core_properties.title='HRNova — Soutenance actualisée : API, accès, PostgreSQL et CI/CD'
    prs.core_properties.modified=datetime(2026,11,4,12)
    prs.core_properties.subject='Recette réelle : 239 tests PostgreSQL, couverture 97,88 %, benchmark HTTP'
    output_dir.mkdir(parents=True,exist_ok=True)
    target=output_dir/(STEM+'.pptx')
    prs.save(target)
    (output_dir/(STEM+'_Notes.md')).write_text('# HRNova — Notes actualisées au 4 novembre 2026\n\n'+f'{total} diapositives ; notes intégrées au PowerPoint.\n\n'+'\n'.join(all_notes))
    preview_dir=output_dir/'apercus_actualises_2026-11-04'
    preview_dir.mkdir(exist_ok=True)
    for number,image in updated_previews:image.save(preview_dir/f'slide_{number:02d}.png')
    columns=3;rows=(len(updated_previews)+columns-1)//columns
    overview=Image.new('RGB',(480*columns,270*rows),'white')
    for i,(_,image) in enumerate(updated_previews):overview.paste(image.resize((480,270)),((i%columns)*480,(i//columns)*270))
    overview.save(output_dir/(STEM+'_Apercu.png'))
    # Vérifier la cohérence des chiffres et l’absence des anciens résultats dans les slides actives.
    check=Presentation(target)
    content='\n'.join(sh.text for sl in check.slides for sh in sl.shapes if sh.has_text_frame)
    assert '239' in content and '97,88 %' in content and 'utilisateur' in content and 'livreur' in content
    assert not re.search(r'\b87\b|\b89 %\b',content)
    for sl in check.slides:
        assert len(notes_frame(sl).text)>0
    print(f'{target.name} : {len(check.slides)} diapositives, {len(updated_previews)} diapositives nouvelles ou actualisées ; notes intégrées.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=OUT/'HRNova_Soutenance_Enrichie_2026-10-29.pptx')
    parser.add_argument('--output-dir',type=Path,default=OUT)
    args=parser.parse_args()
    build(args.source,args.output_dir)
