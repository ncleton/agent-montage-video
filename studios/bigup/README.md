# Studio de tournage Bigup

Copie locale de Bigup (bigup.rossinienergy.com) pour filmer ses tutoriels, selon le skill `studio-de-tournage`.
Tout tourne sur le poste de montage, sur 127.0.0.1. Aucun accès de production : ni secret de passerelle, ni clé
Google, ni jeton HubSpot de Rossini.

| Adresse | Ce que c'est |
|---|---|
| http://127.0.0.1:55813 | Bigup vu par Camille Martin, commerciale fictive, droits de base d'un commercial |
| http://127.0.0.1:55814 | Bigup vu par l'administrateur du studio (réglages seulement, jamais filmé) |

## Démarrer, arrêter, semer

    ./start.sh          # Postgres, migration de la plateforme, Drive du studio, plateforme, Site, relais, score
    seed/all.sh         # entreprises, secteurs de tournée, HubSpot de test, case Prospects (25)
    data/venv/bin/python seed/seed_shared_table.py   # Tableur partagé : la liste des stations de ski (475 lignes)
    ./score.sh          # clients gagnés (portail de test) puis passage de score, relançable à la main
    ./stop.sh

Mettre le studio au code en production : data/site au commit de la dernière version Sites publiée (journal de
publication), puis npm --prefix data/site run build ; data/platform au commit de l'image leadgenerator-platform de
l'API en production (docker ps sur contabo-leadgen) ; puis ./stop.sh et ./start.sh. start.sh applique le schéma de
la plateforme (service provision, comme deploy.sh) et score.sh recalcule le score de chaque prospect : depuis le
21/11/2026, seul le serveur le calcule (row_scores), d'après les clients gagnés qu'il lit dans HubSpot.

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

- Tableur partagé (seed/seed_shared_table.py) : la liste de production « Stations de ski France · recharge et
  ombrières » entière, partagée en lecture à Camille comme Nicolas partage une liste générée sur demande. Chaque
  personne devient un double fictif (contact de ligne, mentions dans les réponses, nom de famille seul ou collé), les
  profils LinkedIn sont retirés ; le semis échoue s'il reste un nom réel. --campaign <id> partage une autre liste
  (Weldom : 72a41e0f-a2e4-420a-8388-bfc86bccd769).
- Images IGN : les scénarios de Bigup portent "cache": {"dir": "work/cache-images", "hosts": ["data\\.geopf\\.fr"]}
  (scripts/studio_chrome.mjs) : le Géoportail refuse les rafales d'orthophotos du Tableur, le cache les sert à
  l'identique au contrôle et au tournage.

- Entreprises réelles d'un livret de production (lecture seule par SSH), avec leurs réponses sourcées, parking,
  cadastre, score et logo. Chaque vraie personne devient un double fictif ; le semis échoue s'il en reste une.
- Case Prospects : 25 prospects, au plus 21 verts selon la note calculée par Bigup, le reste ajouté par Camille.
- Secteurs « Métropole lilloise » et « Aisne et Ardennes » sur les semaines autour de la date du jour.
- HubSpot de test : Camille propriétaire, Pipeline Bornes et Pipeline Ombrières, 8 transactions en cours, 6
  rendez-vous fictifs dans la semaine.

