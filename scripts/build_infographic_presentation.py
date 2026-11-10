"""Refonte graphique native PowerPoint, 19 slides. python-pptx + Pillow."""
from pathlib import Path
from datetime import datetime
import json
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from build_presentation import Deck, ROOT, rgb

OUT=ROOT/'presentations'
STEM='HRNova_Soutenance_Infographie_2026-11-10'
source=Presentation(OUT/'HRNova_Soutenance_Plan_2026-11-10.pptx')
results=json.loads((ROOT/'docs/test_results.json').read_text())
assert results['tests']==263 and results['coverage_percent']==100.0
assert results['covered_lines']==results['measured_lines']==1273
DARK='FFFFFF'; PANEL='F2F6F6'; LIGHT='FFFFFF'; WHITE='37474F'; LIME='1689AC'; VIOLET='6BBEB4'; GRAY='68777B'; INK='37474F'
COLORS=['1689AC','6BBEB4','E6B739','ED786E']
class Modern(Deck):
    def new_page(self,title,label,dark=True):
        self.dark=False
        self.fg=INK; self.muted=GRAY; self.accent=COLORS[(len(self.prs.slides))%4]; self.surface=PANEL
        self.panel_index=0
        self.slide=self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.slide.background.fill.solid(); self.slide.background.fill.fore_color.rgb=rgb('FFFFFF')
        self.canvas=Image.new('RGB',(1600,900),'white'); self.draw=ImageDraw.Draw(self.canvas)
        i=len(self.prs.slides)
        self.text('HRNova',.55,.32,1.8,.35,16,INK,True)
        for j,c in enumerate(COLORS): self.box(.55+j*.24,.78,.22,.035,c)
        self.text(label.upper(),2.2,.38,9,.28,10,GRAY)
        self.text(f'{i:02}',11.65,.3,1.1,.5,22,self.accent,True,align='right')
        self.text(title,.55,1.02,12.2,.94,29,INK,False)
        for j,c in enumerate(COLORS): self.box(.55+j*3.05,7.08,3.05,.025,c)
        self.text('SAMUEL GABBAI  /  DATA SCIENCE & MLOPS',.55,7.22,8,.2,8,GRAY)
        self.text('NOVEMBRE 2026',10.5,7.22,2.25,.2,8,GRAY,align='right')
        note=source.slides[i-1].notes_slide.notes_text_frame.text
        if i == 8:
            note=("Recette PostgreSQL du 10 novembre 2026 : 263 tests réussis, zéro échec "
                  "et zéro test ignoré. Couverture des lignes : 1 273 sur 1 273, soit 100 % "
                  "sur huit modules applicatifs et les scripts opérationnels ; les générateurs "
                  "de présentations sont exclus comme auparavant. Le seuil CI demeure 95 %. "
                  "Les 24 nouveaux cas couvrent surtout les erreurs et les frontières externes "
                  "avec des mocks. La couverture des branches n'est pas activée et 100 % des "
                  "lignes ne garantit pas l'absence de défauts. Source : docs/test_results.json.")
        elif i == 9:
            note += ("\n\nMise à jour du 10 novembre : 24 cas ajoutés, dont les exports "
                     "invalides, les commandes Docker simulées, le client Hugging Face simulé, "
                     "l'attente HTTP, la confirmation du mot de passe et les droits SQL. "
                     "La suite complète atteint 263 tests réussis sur PostgreSQL.")
        elif i == 18:
            note += ("\n\nRecette actualisée au 10 novembre 2026 : 263 tests réussis, "
                     "100 % de couverture des lignes (1 273/1 273). Les frontières Docker et "
                     "Hugging Face sont testées avec des mocks ; leur exécution distante reste "
                     "à confirmer. Source : docs/test_results.json.")
        self.slide.notes_slide.notes_text_frame.text=note
        self.notes.append((title,note,''))
    def txt(self,t,x,y,w,h,size=20,color=None,bold=False):
        return self.text(t,x,y,w,h,size,color or self.fg,bold)
    def circle(self,x,y,r,color):
        sh=self.slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(r), Inches(r))
        sh.fill.solid();sh.fill.fore_color.rgb=rgb(color);sh.line.fill.background()
        self.draw.ellipse((round(x*120),round(y*120),round((x+r)*120),round((y+r)*120)),fill='#'+color)
        return sh
    def panel(self,x,y,w,h,title,lines,number=None):
        c=COLORS[self.panel_index%4];self.panel_index+=1
        self.box(x,y,w,h,'F7F9F9',rounded=True)
        self.box(x+.23,y+.25,.38,.035,c)
        if number:
            self.circle(x+.23,y+.22,.62,c)
            self.text(number,x+.33,y+.39,.45,.3,15,'FFFFFF',True)
            ty=y+1.0
        else: ty=y+.48
        self.text(title,x+.25,ty,w-.5,.65,17,c,True)
        for j,line in enumerate(lines):
            yy=ty+.70+j*.50
            self.circle(x+.27,yy+.10,.055,c)
            self.text(line,x+.48,yy,w-.73,.50,14 if w<4 else 16,INK)
    def takeaway(self,t):
        self.box(.55,6.35,.06,.38,self.accent)
        self.text(t,.77,6.34,11.95,.5,15,self.muted)
    def pill(self,t,x,y,w):
        self.box(x,y,w,.43,self.accent,rounded=True)
        self.text(t,x+.12,y+.1,w-.24,.25,11,DARK,True)
    def rows(self,headers,rows,widths,y=2.15,font=16,row_h=.6):
        xx=.55
        for h,w in zip(headers,widths):
            self.text(h.upper(),xx+.15,y,w-.3,.4,11,self.muted,True);xx+=w
        for i,row in enumerate(rows):
            yy=y+.53+i*row_h
            self.box(.55,yy,12.2,row_h-.07,self.surface,rounded=True)
            xx=.55
            for j,(val,w) in enumerate(zip(row,widths)):
                self.text(val,xx+.15,yy+.12,w-.3,row_h-.19,font,INK if j==0 else self.fg,j==0);xx+=w

d=Modern(19)
d.prs.core_properties.title='HRNova — Soutenance / Infographies'
d.prs.core_properties.created=datetime(2026,11,10)
# 01 — couverture claire inspirée du modèle fourni
d.new_page('Du modèle au service.', '01 / Le projet')
d.circle(6.15,2.05,1.05,'F0F6F5')
d.circle(6.44,2.28,.46,'6BBEB4')
d.box(6.57,2.75,.20,.18,'68777B',rounded=True)
d.text('HRNOVA',.7,3.35,11.95,.85,44,INK,False,align='center')
d.text('UNE API RH SÉCURISÉE, TESTÉE ET TRAÇABLE',.7,4.25,11.95,.5,19,GRAY,False,align='center')
for j,c in enumerate(COLORS):d.box(.55+j*3.05,5.18,3.05,.045,c)
d.text('FastAPI  /  PostgreSQL  /  Machine Learning  /  CI/CD',.7,5.65,11.95,.45,17,GRAY,False,align='center')
s=d.text('github.com/samuelGabbai/P5_Futurisys',.7,6.38,11.95,.35,14,LIME,False,align='center')
s.text_frame.paragraphs[0].runs[0].hyperlink.address='https://github.com/samuelGabbai/P5_Futurisys'
d.finish()
#02 — infographie en cercles
d.new_page('Comprendre le risque de départ.', '02 / Le modèle')
for x,y,c,num,lab in [(4.7,2.18,'6BBEB4','1 470','SALARIÉS'),(3.75,3.52,'1689AC','43','VARIABLES'),(5.65,3.52,'E6B739','237','DÉPARTS'),(4.7,4.37,'ED786E','16,12 %','DE DÉPARTS')]:
    d.circle(x,y,1.85,c)
    d.text(num,x+.1,y+.44,1.65,.55,27,'FFFFFF',True,align='center')
    d.text(lab,x+.1,y+1.1,1.65,.28,10,'FFFFFF',True,align='center')
d.txt('TROIS SOURCES RH',.65,2.75,3,.4,16,LIME,True)
d.txt('SIRH, sondage et évaluation.\nJointure par identifiant salarié.',.65,3.4,3,1.15,17,INK)
d.txt('UNE CLASSIFICATION',9.1,2.75,3.65,.4,16,'ED786E',True)
d.txt('Probabilité de départ,\npuis décision selon le seuil.\nVariables préparées en amont.',9.1,3.4,3.65,1.5,17,INK)
d.takeaway('Aide à l’analyse RH : les associations statistiques ne prouvent pas une causalité.')
d.finish()
#03 chart
d.new_page('Le choix d’une forêt calibrée.', '03 / Comparaison des modèles')
labels=['Dummy','Régression logistique','Random Forest initial','Random Forest optimisé','LightGBM','Random Forest + SMOTE'];values=[.1644,.4968,.4189,.5048,.5226,.4600]
d.txt('F1 MOYEN — VALIDATION CROISÉE À 5 FOLDS',.65,2.05,8,.35,11,GRAY,True)
for i,(lab,val) in enumerate(zip(labels,values)):
    y=2.65+i*.49;d.txt(lab,.65,y,3.65,.33,15,WHITE,i==3)
    d.box(4.4,y+.01,3.7,.23,PANEL,rounded=True);d.box(4.4,y+.01,3.7*val/.6,.23,LIME if i==3 else VIOLET,rounded=True)
    d.txt(f'{val:.4f}'.replace('.',','),8.3,y-.015,.9,.34,14,LIME if i==3 else GRAY)
d.panel(9.55,2.05,3.2,3.95,'MODÈLE RETENU',['300 arbres','Profondeur : 5','Classes équilibrées','Calibration sigmoid'])
d.takeaway('Choix motivé par les non-linéarités et la maîtrise de la complexité ; LightGBM reste compétitif.')
d.finish()
#04 chart
d.new_page('Un seuil qui détecte davantage.', '04 / Performance prédictive',False)
d.txt('17,02 %',.65,2.1,3.5,.9,44,d.muted,True)
d.arrow(4.15,2.56,5.45,2.56,d.accent,3)
d.txt('61,70 %',5.85,2.1,4,.9,48,d.accent,True)
d.txt('Rappel au seuil 0,50',.65,3.12,4,.4,17,d.muted)
d.txt('Rappel au seuil 0,2232',5.85,3.12,5,.4,17,d.muted)
d.rows(['Sur le test','Seuil 0,50','Seuil optimisé'],[['Précision','34,78 %','42,03 %'],['F1','0,2286','0,5000'],['Accuracy','81,63 %','80,27 %']], [5,3.6,3.6],y=3.85,row_h=.53)
d.takeaway('294 salariés test, dont 47 départs • ROC-AUC : 0,7692 • Résultats historiques du notebook.')
d.finish()
#05
d.new_page('Une prédiction, un parcours traçable.', '05 / API — architecture')
for i,(title,lines,num) in enumerate([('CLIENT',['JSON / CSV','Identifiant salarié'],'01'),('FASTAPI',['Authentification','Validation Pydantic'],'02'),('POSTGRESQL',['Écriture des inputs','Relecture ordonnée'],'03'),('MODÈLE',['Calcul en mémoire','Probabilité / classe'],'04')]):
    x=.55+i*3.12;d.panel(x,2.2,2.85,3.05,title,lines,num)
    if i<3:d.arrow(x+2.88,3.6,x+3.08,3.6,LIME)
d.txt('Retour : validation → stockage des outputs → relecture → réponse HTTP',.7,5.65,12,.45,19,LIME)
d.takeaway('Swagger : 127.0.0.1:8000/docs  •  X-Request-ID relie la requête, les entrées et les sorties.')
d.finish()
#06
d.new_page('Neuf endpoints. Des accès définis.', '06 / API — contrat')
d.rows(['Route','Usage','Droit'],[['GET /health','Disponibilité','Public'],['GET /auth/me','Identité et permissions','Compte actif'],['GET /features','Contrat des 43 variables','Utilisateur'],['POST /predict','Prédiction JSON','Utilisateur'],['POST /predict/file · /predict-proba/file','Classes / probabilités CSV','Utilisateur'],['POST /score/file','Métriques sur CSV étiqueté','Utilisateur'],['GET /employees/{id}/score','Score du profil stocké','Utilisateur'],['GET /model/download','Archive du modèle','Livreur']], [6,3.9,2.3],y=1.98,font=13,row_h=.445)
d.takeaway('Admin cumule les droits. JSON / salarié : seuil optimisé ; /predict/file : décision native.')
d.finish()
#07
d.new_page('Pydantic : le contrat devient exécutable.', '07 / API — validation',False)
d.panel(.55,2.15,5.95,3.65,'ENTRÉES',['43 noms de variables attendus','Valeurs numériques finies','Aucun champ absent ou supplémentaire','Rejet des booléens, null et NaN'],'01')
d.panel(6.8,2.15,5.95,3.65,'SORTIES',['Probabilités bornées entre 0 et 1','Classes limitées à 0 et 1','Une prédiction par ligne','Somme des probabilités égale à 1'],'02')
d.takeaway('Donnée d’entrée non conforme → HTTP 422. La validation ne remplace pas la préparation métier.')
d.finish()
#08
d.new_page('La qualité, preuves à l’appui.', '08 / Couverture de code')
d.txt('100',.65,2.05,6,1.65,98,LIME,True);d.txt('%',3.55,2.6,1.2,.9,45,LIME,True)
d.txt('DES LIGNES COUVERTES',.75,3.95,8,.4,15,GRAY,True)
d.box(.75,4.65,7.3,.16,PANEL,rounded=True);d.box(.75,4.65,7.3,.16,LIME,rounded=True)
d.txt('Seuil CI : 95 %',.75,5.15,7,.4,19,WHITE)
d.panel(8.75,2.15,4,3.7,'263 TESTS RÉUSSIS',['PostgreSQL temporaire','1 273 / 1 273 lignes','24 nouveaux cas avec mocks','Recette du 10/11/2026'])
d.takeaway('Même périmètre et mêmes exclusions. Couverture des branches non activée ; 100 % ≠ absence de bugs.')
d.finish()
#09
d.new_page('Tester aussi ce qui peut échouer.', '09 / Tests unitaires & fonctionnels',False)
d.panel(.55,2.2,3.92,3.7,'UNITAIRES',['Contrats de données','Permissions et rôles','Erreurs du modèle','Limites des fichiers'],'01')
d.panel(4.69,2.2,3.92,3.7,'INTÉGRATION',['Base PostgreSQL isolée','Contraintes et doublons','Transactions / rollback','Persistance des sorties'],'02')
d.panel(8.83,2.2,3.92,3.7,'HTTP RÉEL',['Appels authentifiés','Refus 401 / 403','48 requêtes mesurées','0 erreur au benchmark'],'03')
d.takeaway('24 nouveaux cas ciblent les erreurs et les services simulés. Base de test temporaire, supprimée après recette.')
d.finish()
#10 diagram
d.new_page('Le modèle relationnel de la traçabilité.', '10 / BDD — UML simplifié')
def node(x,y,w,title,body):
    d.box(x,y,w,.95,PANEL,rounded=True);d.txt(title,x+.15,y+.13,w-.3,.3,15,LIME,True);d.txt(body,x+.15,y+.52,w-.3,.3,10,GRAY)
def link(x1,y1,x2,y2,lab,tx,ty,w=1.8):
    d.arrow(x1,y1,x2,y2,VIOLET,1.5);d.txt(lab,tx,ty,w,.25,10,VIOLET)
node(.55,2.15,3.3,'surveys','PK/FK employee_id · UK code_sondage')
node(5,2.15,3.3,'employees','PK id_employee · attributs RH')
node(9.45,2.15,3.3,'evaluations','PK/FK employee_id · UK eval_number')
link(5,2.65,3.85,2.65,'1 → 0..1',3.86,2.28,1.12)
link(8.3,2.65,9.45,2.65,'1 → 0..1',8.33,2.28,1.1)
node(.55,3.75,3.3,'model_versions','PK sha256 · seuil · variables')
node(5,3.75,3.3,'prepared_employees','PK/FK salarié + version · features JSONB')
link(3.85,4.2,5,4.2,'1 → 0..N',3.86,3.86,1.12)
link(6.65,3.1,6.65,3.75,'1 → 0..N',6.8,3.32)
node(.55,5.35,3.3,'api_exchanges','PK id · FK version nullable · statut · durée')
node(5,5.35,3.3,'model_inputs','FK échange / salarié · UK échange + ligne')
node(9.45,5.35,3.3,'model_outputs','PK/FK échange · payload JSONB')
link(2.2,4.7,2.2,5.35,'0..1 → 0..N',2.35,4.92)
link(3.85,5.83,5,5.83,'1 → 0..N',3.86,5.48,1.12)
# Output relation routes through the free right-hand area.
d.arrow(3.85,6.05,4.15,6.05,VIOLET,1)
d.arrow(4.15,6.05,4.15,6.58,VIOLET,1)
d.arrow(4.15,6.58,11.1,6.58,VIOLET,1)
d.arrow(11.1,6.58,11.1,6.3,VIOLET,1)
d.txt('échange 1 → 0..1 sortie',8.4,6.68,3.5,.25,10,VIOLET)
d.txt('Salarié 0..1 → 0..N inputs\nPK : clé primaire · FK : référence\nUK : unicité',9.45,3.7,3.3,1,12,GRAY)
d.finish()
#11
d.new_page('Des données structurées, des volumes bornés.', '11 / BDD — stockage & analytique',False)
for i,(v,l) in enumerate([('1 470','lignes par source'),('10 MiB','taille maximale CSV'),('10 000','lignes CSV maximum')]):
    x=.65+i*4.18;d.txt(v,x,2.15,3.8,.85,42,d.accent,True);d.txt(l,x,3.12,3.8,.4,17,d.muted)
d.panel(.55,4.05,5.95,1.95,'INTÉGRITÉ',['PK / FK / unicité · transactions · index'])
d.panel(6.8,4.05,5.95,1.95,'BESOINS ANALYTIQUES',['Activité, erreurs, scores agrégés (groupes ≥ 5)'])
d.takeaway('JSONB pour features et résultats. Vues analytiques disponibles ; tableau de bord à construire.')
d.finish()
#12
d.new_page('Local aujourd’hui. Cible distante définie.', '12 / BDD — installation & simulation')
d.panel(.55,2.2,5.95,3.5,'LOCAL VÉRIFIÉ',['PostgreSQL 18 · 127.0.0.1:5433','Base hrnova · schéma public','Rôle hrnova_app à droits limités','Script : initialisation + import'])
d.panel(6.8,2.2,5.95,3.5,'DISTANT — SIMULATION',['Client → HTTPS → API conteneurisée','PostgreSQL sur réseau privé','DATABASE_URL injectée au déploiement','Sauvegardes et supervision à prévoir'])
d.takeaway('Démarrer : uv run --no-sync python scripts/local_postgres.py start')
d.finish()
#13 — frise de processus colorée
d.new_page('Git donne une histoire à chaque livraison.', '13 / Versionnement')
d.box(1.65,3.55,9.7,.035,'D9E5E4')
for i,(title,body) in enumerate([('BRANCHE','Isoler une évolution'),('COMMIT','Expliquer le changement'),('PULL REQUEST','Relire et tester'),('FUSION','Valider une version')]):
    x=.65+i*3.12;c=COLORS[i]
    d.circle(x+.85,2.65,.85,c)
    d.text(f'0{i+1}',x+1,2.9,.55,.35,20,'FFFFFF',True,align='center')
    d.circle(x+1.18,3.48,.18,c)
    d.box(x,3.95,2.7,.58,c,rounded=True)
    d.text(title,x+.12,4.13,2.46,.3,13,'FFFFFF',True,align='center')
    d.text(body,x,4.95,2.7,.8,17,INK,False,align='center')
s=d.text('github.com/samuelGabbai/P5_Futurisys',.7,5.8,12,.4,20,LIME,True,align='center')
s.text_frame.paragraphs[0].runs[0].hyperlink.address='https://github.com/samuelGabbai/P5_Futurisys'
d.takeaway('Conventions documentées • commit lié à l’export • .env et données locales ignorés par Git.')
d.finish()
#14
d.new_page('Un dépôt organisé par responsabilité.', '14 / Arborescence')
d.box(.55,2.05,7.55,4.65,PANEL,rounded=True)
d.pill('P5_FUTURISYS /',.8,2.28,2.5)
d.txt('├── api.py · schemas.py · auth.py\n├── inference.py · audit.py · model_release.py\n├── database.py · create_db.py · migrations/\n├── Data/ · artifacts/ · *.ipynb\n├── tests/ · scripts/\n├── docs/ · presentations/\n├── .github/workflows/ci.yml\n├── deployment/compose.yml · Dockerfile\n└── pyproject.toml · uv.lock',.85,3,6.95,3.5,17,WHITE)
d.txt('SERVICE',8.65,2.4,4,.4,13,LIME,True);d.txt('Routes, contrats, sécurité\net persistance.',8.65,3,4,.85,21)
d.txt('OPÉRATIONS',8.65,4.25,4,.4,13,VIOLET,True);d.txt('Tests, documentation,\nlivraison et déploiement.',8.65,4.85,4,1,21)
d.finish()
#15
d.new_page('Du push aux contrôles de livraison.', '15 / GitHub Actions')
for i,(a,ls) in enumerate([('TESTER',['uv.lock + PostgreSQL','Pytest · couverture ≥ 95 %']),('CONSTRUIRE',['Package + documentation','Docker + smoke HTTP']),('LIVRER',['Export modèle validé','Déploiement conditionnel'])]):
    d.panel(.55+i*4.14,2.15,3.92,3.15,a,ls,f'0{i+1}')
d.txt('development   →   staging / develop   →   production / main',.7,5.65,12,.45,20,LIME,True)
d.takeaway('YAML configuré. Exécution GitHub et build distant à confirmer ; déploiement API soumis à configuration.')
d.finish()
#16
d.new_page('Les secrets restent hors du dépôt.', '16 / Sécurité',False)
d.panel(.55,2.1,5.95,3.6,'SUR LA MACHINE',['.env : DATABASE_URL et comptes','Fichiers protégés en 0600','PBKDF2-SHA256 + sel aléatoire','600 000 itérations de hachage'])
d.panel(6.8,2.1,5.95,3.6,'DANS LE PIPELINE',['Secrets GitHub par environnement','HF_TOKEN pour publier uniquement','Compte livreur / admin requis','HTTPS à prévoir pour l’accès distant'])
d.takeaway('Utilisateur → API métier   /   Livreur → livraison   /   Admin → les deux')
d.finish()
#17
d.new_page('Hugging Face distribue l’artefact validé.', '17 / Publication du modèle')
d.panel(.55,2.15,5.3,3.8,'LE PAQUET LIVRÉ',['turnover_model.joblib','metadata.json : hash + commit','requirements.txt + README.md','Dictionnaire des salariés exclu'])
d.arrow(6.05,3.9,6.85,3.9,LIME,3)
d.panel(7.1,2.15,5.65,3.8,'DÉPÔT MODEL CIBLE',['huggingface.co/SamGabb/hrnova','Compte livreur/admin + HF_TOKEN','Export issu du commit validé','Publication effective à vérifier'])
d.takeaway('Publier un modèle ne lance pas une API en ligne et ne réentraîne pas le modèle.')
d.finish()
#18
d.new_page('Le service est construit. Les preuves existent.', '18 / Bilan',False)
d.rows(['Action','Résultat'],[['EXPOSER','9 endpoints · Swagger · validation Pydantic'],['SÉCURISER','Rôles applicatifs + droits SQL limités'],['TRACER','Sources, versions, entrées, sorties et erreurs'],['VÉRIFIER','263 tests · 100 % des lignes au 10/11/2026'],['DOCUMENTER','MkDocs · benchmark · vues analytiques'],['PRÉPARER LA LIVRAISON','YAML + Docker + export Hugging Face']], [4.4,7.8],y=2.05,font=16,row_h=.55)
d.takeaway('Exploitation locale documentée ; mise en service distante encore à valider.')
d.finish()
#19 — trois axes sous forme d’infographie
d.new_page('La suite : fiabiliser, puis industrialiser.', '19 / Améliorations')
for i,(title,lines) in enumerate([('MODÈLE',['Pipeline de préparation sur le train','Validation temporelle','Analyse des erreurs par population']),('EXPLOITATION',['CI et déploiement distant','HTTPS, rotation et restauration','Charge et supervision']),('PILOTAGE',['Tableau de bord agrégé','Suivi de la dérive','Rétention et réévaluation'])]):
    x=.55+i*4.14;c=COLORS[i]
    d.circle(x+1.2,2.12,1.45,c)
    d.text(f'0{i+1}',x+1.43,2.52,.99,.6,32,'FFFFFF',True,align='center')
    d.text(title,x,3.95,3.92,.4,18,INK,True,align='center')
    for j,line in enumerate(lines):d.text(line,x,4.65+j*.48,3.92,.45,14,GRAY,False,align='center')
d.takeaway('Prochaine étape : prouver une livraison reproductible de bout en bout sur la cible retenue.')
d.finish()

assert len(d.prs.slides)==19
d.prs.save(OUT/f'{STEM}.pptx')
previews=OUT/'apercus_infographie_2026-11-10';previews.mkdir(exist_ok=True)
overview=Image.new('RGB',(1600,1125),'#'+DARK)
for i,img in enumerate(d.images):
    img.save(previews/f'slide_{i+1:02d}.png');overview.paste(img.resize((400,225)),((i%4)*400,(i//4)*225))
overview.save(OUT/f'{STEM}_Apercu.png')
notes=['# HRNova — Infographies / Notes orateur','']
for i,(t,n,_) in enumerate(d.notes,1):notes.extend([f'## {i:02} — {t}','',n,''])
(OUT/f'{STEM}_Notes.md').write_text('\n'.join(notes))
print(f'{STEM}: 19 diapositives, notes et aperçus')
