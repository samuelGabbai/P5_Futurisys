# Présentation de soutenance HRNova

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
