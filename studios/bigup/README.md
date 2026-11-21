# Studio de tournage Bigup

Copie locale de Bigup (bigup.rossinienergy.com) pour filmer ses tutoriels, selon le skill `studio-de-tournage`.
Tout tourne sur le poste de montage, sur 127.0.0.1. Aucun accès de production : ni secret de passerelle, ni clé
Google, ni jeton HubSpot de Rossini.

| Adresse | Ce que c'est |
|---|---|
| http://127.0.0.1:55813 | Bigup vu par Camille Martin, commerciale fictive, droits de base d'un commercial |
| http://127.0.0.1:55814 | Bigup vu par l'administrateur du studio (réglages seulement, jamais filmé) |

## Démarrer, arrêter, semer

    ./start.sh          # Postgres, Drive du studio, plateforme, Site, relais d'identité
    seed/all.sh         # entreprises, secteurs de tournée, HubSpot de test, case Prospects (25)
    ./stop.sh

Le contrôle avant tournage : `node ../../scripts/studio_check.mjs <scenario.json> <sortie>` (règle 6 du studio).

## Ce que contient `data/` (hors Git)

- `platform/` et `site/` : copies de sales-marketplace et leadgenerator-site au commit en production ; `venv/` ;
  `pg/` et `pgdata/` (Postgres 17 natif, micromamba) ; `documents/` (logos copiés).
- `gateway-secret`, `runtime-password`, `pg-password` : secrets du studio seulement, tirés au hasard.
- `hubspot-test-token` : jeton de l'application privée « Studio Bigup » du portail de test développeur 149831332
  (compte développeur 149831328 de nicolas@rossinienergy.com, créé le 21/11/2026). `start.sh` refuse tout autre
  type de portail et le portail de Rossini (6053297). Le portail de test expire après 90 jours sans appel d'API :
  chaque semis le prolonge.
- `drive-snapshot.json` : instantané en lecture seule du Drive partagé « Bigup · Documents communs », lu avec le
  connecteur Google Drive (dossiers, noms, types, liens). Pour le rafraîchir : relire le Drive partagé
  0ACtpltj6bPe6Uk9PVA sur trois niveaux avec le connecteur et réécrire ce fichier, puis relancer `./start.sh`.

## Données de vitrine

- Entreprises réelles d'un livret de production (lecture seule par SSH), avec leurs réponses sourcées, parking,
  cadastre, score et logo. Chaque vraie personne devient un double fictif ; le semis échoue s'il en reste une.
- Case Prospects : 25 prospects, au plus 21 verts selon la note calculée par Bigup, le reste ajouté par Camille.
- Secteurs « Métropole lilloise » et « Aisne et Ardennes » sur les semaines autour de la date du jour.
- HubSpot de test : Camille propriétaire, Pipeline Bornes et Pipeline Ombrières, 8 transactions en cours, 6
  rendez-vous fictifs dans la semaine.

