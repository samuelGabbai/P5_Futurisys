# Contrat des variables d'entrée

L'API attend les **43 variables numériques préparées**, sans cible ni identifiant.
`GET /features` donne la liste de référence pour le modèle chargé. L'ordre d'envoi
est libre, mais les noms doivent correspondre exactement, accents et espaces compris.
Les noms source ont été conservés pour rester compatibles avec l'artefact.

Le tableau suivant décrit l'export examiné le 27 octobre 2026. Il doit être mis à jour
avec le modèle. Les conversions de pourcentage, encodages et ratios se font en amont,
dans le notebook, pas dans l'API.

| Variable | Signification et préparation |
| --- | --- |
| `nombre_participation_pee` | Nombre de participations au plan d'épargne, valeur source |
| `nb_formations_suivies` | Nombre de formations, valeur source |
| `nombre_employee_sous_responsabilite` | Nombre source de salariés sous responsabilité ; constant dans le cas d'étude |
| `distance_domicile_travail` | Distance source ; unité non précisée dans les fichiers |
| `niveau_education` | Niveau d'éducation ordinal de la source |
| `ayant_enfants` | `Y → 1`, `N → 0` ; constant à 1 dans le dataset fourni |
| `frequence_deplacement` | `Aucun → 0`, `Occasionnel → 1`, `Frequent → 2` |
| `annees_depuis_la_derniere_promotion` | Années depuis la promotion |
| `annes_sous_responsable_actuel` | Années avec le responsable actuel ; orthographe source conservée |
| `age` | Âge en années |
| `revenu_mensuel` | Revenu mensuel ; devise non précisée dans les fichiers |
| `nombre_experiences_precedentes` | Nombre d'expériences précédentes |
| `nombre_heures_travailless` | Mesure source du nombre d'heures ; période non précisée |
| `annee_experience_totale` | Expérience totale en années |
| `annees_dans_l_entreprise` | Ancienneté en années |
| `annees_dans_le_poste_actuel` | Années dans le poste |
| `note_evaluation_precedente` | Note source de l'évaluation précédente |
| `niveau_hierarchique_poste` | Niveau hiérarchique ordinal source |
| `note_evaluation_actuelle` | Note source de l'évaluation actuelle |
| `heure_supplementaires` | `Non → 0`, `Oui → 1` |
| `augementation_salaire_precedente` | Pourcentage sans symbole : `11 % → 11.0`, pas `0.11` |
| `genreIsMale` | `M → 1`, `F → 0` dans les données fournies |
| `IsMarried` | Marié(e) : 1 ; Célibataire ou Divorcé(e) : 0 |
| `IsSingle` | Célibataire ou Divorcé(e) : 1 ; Marié(e) : 0 |
| `jeune_sous_paye` | 1 si âge < 30 et revenu inférieur à la médiane de référence |
| `sous_paye_moyenne` | 1 si revenu inférieur à la médiane de référence, malgré le nom source « moyenne » |
| `ratio_salaire_edu_anciennete` | Revenu / médiane du groupe niveau d'éducation × tranche d'ancienneté |
| `satisfaction_globale` | Moyenne des quatre satisfactions source : environnement, nature du travail, équipe, équilibre vie pro/perso |
| `domaine_etude_Entrepreunariat` | Indicateur one-hot de la catégorie portant ce nom source |
| `domaine_etude_Infra & Cloud` | Indicateur one-hot |
| `domaine_etude_Marketing` | Indicateur one-hot |
| `domaine_etude_Ressources Humaines` | Indicateur one-hot |
| `domaine_etude_Transformation Digitale` | Indicateur one-hot |
| `departement_Consulting` | Indicateur one-hot |
| `departement_Ressources Humaines` | Indicateur one-hot |
| `poste_Cadre Commercial` | Indicateur one-hot |
| `poste_Consultant` | Indicateur one-hot |
| `poste_Directeur Technique` | Indicateur one-hot |
| `poste_Manager` | Indicateur one-hot |
| `poste_Représentant Commercial` | Indicateur one-hot |
| `poste_Ressources Humaines` | Indicateur one-hot |
| `poste_Senior Manager` | Indicateur one-hot |
| `poste_Tech Lead` | Indicateur one-hot |

Une catégorie de référence est retirée par `drop="first"`. Pour cette version,
les références correspondent à `Autre` pour le domaine, `Commercial` pour le
département et `Assistant de Direction` pour le poste. Des indicateurs tous nuls
peuvent aussi résulter d'une catégorie inconnue, puisque l'encodeur ignore ces catégories.
Il faut donc conserver le vocabulaire et les règles de préparation associés à la version.

Les tranches d'ancienneté du ratio utilisent les bornes `[0, 2, 5, 10, 20, 50]`
avec `include_lowest=True`. Recalculer les médianes sur chaque petit fichier envoyé
modifierait le sens des variables : utiliser les références du jeu d'entraînement.
Le notebook actuel calcule ces références avant le split ; cette limite et sa
correction recommandée sont décrites dans [la fiche modèle](model.md).

Pydantic contrôle que chaque valeur est numérique et finie. Il n'impose pas encore
toutes les bornes métier, par exemple un âge plausible, ni les relations entre les
indicateurs one-hot. Une entrée acceptée techniquement n'est donc pas forcément
représentative des données d'entraînement.
