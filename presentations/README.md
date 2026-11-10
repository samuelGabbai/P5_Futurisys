# Présentation de soutenance HRNova

## Version Infographie — inspirée de la référence visuelle

- [PowerPoint — 19 diapositives](HRNova_Soutenance_Infographie_2026-11-10.pptx)
- [Aperçu](HRNova_Soutenance_Infographie_2026-11-10_Apercu.png)
- [Notes orateur](HRNova_Soutenance_Infographie_2026-11-10_Notes.md)

Fond blanc, palette bleu/turquoise/jaune/corail, infographies en cercles et frise Git. Formes et textes éditables. Générateur : `scripts/build_infographic_presentation.py`.
Résultats qualité actualisés au 10 novembre 2026 sur les diapositives 8, 9 et 18 : 263 tests réussis et 100 % des lignes couvertes (1 273/1 273). Les notes orateur et l'aperçu reprennent ces chiffres.


## Version Design — 19 diapositives

- [PowerPoint modernisé](HRNova_Soutenance_Design_2026-11-10.pptx)
- [Aperçu complet](HRNova_Soutenance_Design_2026-11-10_Apercu.png)
- [Notes orateur](HRNova_Soutenance_Design_2026-11-10_Notes.md)

Palette bleu nuit, citron et violet ; alternance de fonds clairs et sombres, graphique F1, chiffres clés et diagrammes éditables. Le plan et les notes sont conservés. Générateur : `scripts/build_design_presentation.py` (python-pptx et Pillow).


## Version selon le plan demandé — 10 novembre 2026

- [PowerPoint — 19 diapositives](HRNova_Soutenance_Plan_2026-11-10.pptx)
- [Notes orateur](HRNova_Soutenance_Plan_2026-11-10_Notes.md), également intégrées au PPT
- [Aperçu des 19 diapositives](HRNova_Soutenance_Plan_2026-11-10_Apercu.png)

Plan : contexte projet (1), contexte modèle (1), métriques et choix (2), API et Pydantic (3), couverture et tests (2), BDD (3), Git (1), arborescence (1), GitHub Actions (1), secrets (1), Hugging Face (1), bilan (1), améliorations (1).

Générateur : `scripts/build_focused_presentation.py` (python-pptx 1.0.2 et Pillow). Les résultats de tests sont datés du 4 novembre ; les métriques ML sont historiques. Le distant est présenté comme configuration ou simulation à valider. Le lien GitHub est cliquable. La version précédente est conservée.

## Version précédente

Version actualisée au **4 novembre 2026** :

- [PowerPoint — 34 diapositives](HRNova_Soutenance_Actualisee_2026-11-04.pptx)
- [Notes orateur](HRNova_Soutenance_Actualisee_2026-11-04_Notes.md), également intégrées au PowerPoint
- [Aperçu des diapositives nouvelles ou actualisées](HRNova_Soutenance_Actualisee_2026-11-04_Apercu.png)

La nouvelle version conserve les diapositives non remplacées du fichier
`HRNova_Soutenance_Enrichie_2026-10-29.pptx`, avec ses retouches manuelles. Elle
actualise les droits utilisateur/livreur/admin, les routes API, le lancement et la
connexion, les preuves PostgreSQL, le benchmark, les vues analytiques, les
conventions Git et la chaîne CI/CD. Les métriques du modèle restent identifiées
comme historiques ; le build Docker distant reste à confirmer dans GitHub Actions.

Le générateur `scripts/build_updated_presentation.py` utilise `python-pptx==1.0.2`
et Pillow ; il produit une nouvelle copie et ne remplace pas le support source.
