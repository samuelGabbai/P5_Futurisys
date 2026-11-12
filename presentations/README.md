# Présentation de soutenance HRNova

La [présentation infographique](HRNova_Soutenance_Infographie_2026-11-10.pptx)
contient 19 diapositives et leurs notes orateur. Elle présente le contexte, le
modèle, l'API, PostgreSQL, Git, la CI/CD et les pistes d'amélioration. Les résultats
qualité datés du 10 novembre 2026 sont : **263 tests réussis** et **100 % des lignes
couvertes** (1 273/1 273) sur le périmètre mesuré.

Le générateur [build_infographic_presentation.py](../scripts/build_infographic_presentation.py)
utilise le PPT livré pour conserver les notes orateur. Il requiert
`python-pptx==1.0.2` et Pillow. Les images d'aperçu sont des sorties de génération
et ne sont pas nécessaires pour ouvrir la présentation.
