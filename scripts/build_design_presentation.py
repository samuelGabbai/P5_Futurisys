"""Refonte graphique native PowerPoint, 19 slides. python-pptx + Pillow."""
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from build_presentation import Deck, ROOT, rgb

OUT=ROOT/'presentations'
STEM='HRNova_Soutenance_Design_2026-11-10'
source=Presentation(OUT/'HRNova_Soutenance_Plan_2026-11-10.pptx')
DARK='10131D'; PANEL='1C2130'; LIGHT='F3F2ED'; WHITE='FFFFFF'; LIME='D4F878'; VIOLET='A89AFF'; GRAY='A5ADBF'; INK='191E2B'
class Modern(Deck):
    def new_page(self,title,label,dark=True):
        self.dark=dark
        self.fg=WHITE if dark else INK
        self.muted=GRAY if dark else '606879'
        self.accent=LIME if dark else '6251B5'
        self.surface=PANEL if dark else WHITE
        self.slide=self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.slide.background.fill.solid(); self.slide.background.fill.fore_color.rgb=rgb(DARK if dark else LIGHT)
        self.canvas=Image.new('RGB',(1600,900),'#'+(DARK if dark else LIGHT)); self.draw=ImageDraw.Draw(self.canvas)
        i=len(self.prs.slides)
        self.text('HRNOVA',.55,.32,1.8,.32,13,self.fg,True)
        self.text(label.upper(),2.2,.34,9,.28,10,self.muted)
        self.text(f'{i:02}',11.65,.27,1.1,.55,25,self.accent,True,align='right')
        self.text(title,.55,.98,12.2,1.04,32,self.fg,True)
        self.box(.55,7.08,12.2,.012,'343A48' if dark else 'D8D9D5')
        self.box(.55,7.08,12.2*i/19,.025,self.accent)
        self.text('SAMUEL GABBAI  /  DATA SCIENCE & MLOPS',.55,7.22,8,.2,8,self.muted)
        self.text('NOVEMBRE 2026',10.5,7.22,2.25,.2,8,self.muted,align='right')
        note=source.slides[i-1].notes_slide.notes_text_frame.text
        self.slide.notes_slide.notes_text_frame.text=note
        self.notes.append((title,note,''))
    def txt(self,t,x,y,w,h,size=20,color=None,bold=False):
        return self.text(t,x,y,w,h,size,color or self.fg,bold)
    def panel(self,x,y,w,h,title,lines,number=None):
        self.box(x,y,w,h,self.surface,rounded=True)
        if number:
            self.text(number,x+.25,y+.22,w-.5,.62,30,self.accent,True)
            ty=y+.85
        else: ty=y+.28
        self.text(title,x+.25,ty,w-.5,.65,19,self.accent,True)
        for j,line in enumerate(lines):
            yy=ty+.72+j*.52
            self.box(x+.27,yy+.08,.06,.06,self.accent)
            self.text(line,x+.48,yy,w-.73,.50,14 if w<4 else 16,self.fg)
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
                self.text(val,xx+.15,yy+.12,w-.3,row_h-.19,font,self.accent if j==0 else self.fg,j==0);xx+=w

d=Modern(19)
d.prs.core_properties.title='HRNova — Soutenance / Design'
d.prs.core_properties.created=datetime(2026,11,10)
# 01 — cover with editorial typography and architecture illustration
d.new_page('Du modèle au service.', '01 / Le projet')
d.txt('Prédire.\nSécuriser.\nTracer.',.62,2.15,6.9,2.75,48,WHITE,True)
d.txt('Une API RH locale, testée et reproductible.',.65,5.35,7,.65,20,GRAY)
for i,(title,sub) in enumerate([('MODEL','Random Forest calibré'),('API','FastAPI + Pydantic'),('DATA','PostgreSQL + SQLAlchemy')]):
    x=8.35+(i%2)*.3;y=2.05+i*1.28
    d.box(x,y,3.8,1.06,PANEL,rounded=True);d.txt(title,x+.22,y+.15,3.3,.35,18,LIME,True);d.txt(sub,x+.22,y+.61,3.3,.3,12,GRAY)
    if i<2:d.arrow(x+1.9,y+1.08,x+1.9,y+1.25,LIME)
s=d.txt('github.com/samuelGabbai/P5_Futurisys',.65,6.4,10,.4,16,LIME)
s.text_frame.paragraphs[0].runs[0].hyperlink.address='https://github.com/samuelGabbai/P5_Futurisys'
d.finish()
#02
d.new_page('Comprendre le risque de départ.', '02 / Le modèle',False)
for x,num,lab in [(.65,'1 470','salariés distincts'),(4.95,'43','variables préparées'),(9.2,'16,12 %','de départs observés')]:
    d.txt(num,x,2.05,3.5,.9,46,d.accent,True);d.txt(lab,x,3.05,3.5,.4,17,d.muted)
d.panel(.55,4,5.95,1.9,'SOURCES RH',['SIRH + sondage + évaluation'])
d.panel(6.8,4,5.95,1.9,'CLASSIFICATION BINAIRE',['Probabilité → seuil → classe 0 / 1'])
d.takeaway('237 départs sur 1 470 salariés. L’API reçoit des variables préparées, pas les CSV RH bruts.')
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
d.txt('97,88',.65,2.05,7,1.65,98,LIME,True);d.txt('%',7.0,2.6,1.2,.9,45,LIME,True)
d.txt('DE COUVERTURE MESURÉE',.75,3.95,8,.4,15,GRAY,True)
d.box(.75,4.65,7.3,.16,PANEL,rounded=True);d.box(.75,4.65,7.3*.9788,.16,LIME,rounded=True)
d.txt('Seuil CI : 95 %',.75,5.15,7,.4,19,WHITE)
d.panel(8.75,2.15,4,3.7,'239 TESTS RÉUSSIS',['PostgreSQL réel','0 échec / 0 ignoré','Rapports JUnit + couverture','Recette du 04/11/2026'])
d.takeaway('Périmètre : 8 modules + scripts opérationnels ; générateurs de PPT exclus. Couverture ≠ absence de bugs.')
d.finish()
#09
d.new_page('Tester aussi ce qui peut échouer.', '09 / Tests unitaires & fonctionnels',False)
d.panel(.55,2.2,3.92,3.7,'UNITAIRES',['Contrats de données','Permissions et rôles','Erreurs du modèle','Limites des fichiers'],'01')
d.panel(4.69,2.2,3.92,3.7,'INTÉGRATION',['Base PostgreSQL isolée','Contraintes et doublons','Transactions / rollback','Persistance des sorties'],'02')
d.panel(8.83,2.2,3.92,3.7,'HTTP RÉEL',['Appels authentifiés','Refus 401 / 403','48 requêtes mesurées','0 erreur au benchmark'],'03')
d.takeaway('Base de test temporaire, supprimée en fin de recette. Le benchmark ne constitue pas un SLA.')
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
#13
d.new_page('Git donne une histoire à chaque livraison.', '13 / Versionnement',False)
for i,(a,b) in enumerate([('BRANCHE','Isoler une évolution'),('COMMIT','Expliquer le changement'),('PULL REQUEST','Relire et tester'),('FUSION','Valider une version')]):
    x=.55+i*3.12;d.panel(x,2.3,2.85,2.7,a,[b],f'0{i+1}')
    if i<3:d.arrow(x+2.87,3.55,x+3.08,3.55,d.accent)
s=d.txt('github.com/samuelGabbai/P5_Futurisys',.7,5.5,12,.55,24,d.accent,True)
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
d.rows(['Action','Résultat'],[['EXPOSER','9 endpoints · Swagger · validation Pydantic'],['SÉCURISER','Rôles applicatifs + droits SQL limités'],['TRACER','Sources, versions, entrées, sorties et erreurs'],['VÉRIFIER','239 tests · couverture 97,88 % au 04/11/2026'],['DOCUMENTER','MkDocs · benchmark · vues analytiques'],['PRÉPARER LA LIVRAISON','YAML + Docker + export Hugging Face']], [4.4,7.8],y=2.05,font=16,row_h=.55)
d.takeaway('Exploitation locale documentée ; mise en service distante encore à valider.')
d.finish()
#19
d.new_page('La suite : fiabiliser, puis industrialiser.', '19 / Améliorations')
for i,(a,ls) in enumerate([('MODÈLE',['Préparation ajustée sur le train','Pipeline sérialisable','Validation temporelle','Erreurs par population']),('EXPLOITATION',['Preuve CI / déploiement distant','HTTPS et rotation des secrets','Sauvegarde + restauration','Charge et supervision']),('PILOTAGE',['Tableau de bord agrégé','Suivi de la dérive','Rétention des données','Réévaluation du modèle'])]):
    d.panel(.55+i*4.14,2.15,3.92,3.85,a,ls,f'0{i+1}')
d.takeaway('Prochaine étape : prouver une livraison reproductible de bout en bout sur la cible retenue.')
d.finish()

assert len(d.prs.slides)==19
d.prs.save(OUT/f'{STEM}.pptx')
previews=OUT/'apercus_design_2026-11-10';previews.mkdir(exist_ok=True)
overview=Image.new('RGB',(1600,1125),'#'+DARK)
for i,img in enumerate(d.images):
    img.save(previews/f'slide_{i+1:02d}.png');overview.paste(img.resize((400,225)),((i%4)*400,(i//4)*225))
overview.save(OUT/f'{STEM}_Apercu.png')
notes=['# HRNova — Design / Notes orateur','']
for i,(t,n,_) in enumerate(d.notes,1):notes.extend([f'## {i:02} — {t}','',n,''])
(OUT/f'{STEM}_Notes.md').write_text('\n'.join(notes))
print(f'{STEM}: 19 diapositives, notes et aperçus')
