# Studio de tournage Bigup

Copie locale de Bigup (bigup.rossinienergy.com) pour filmer ses tutoriels, selon le skill `studio-de-tournage`.
Tout tourne sur le poste de montage, sur 127.0.0.1. Aucun accès de production : ni secret de passerelle, ni jeton
HubSpot de Rossini. Seule exception, décidée par Nicolas le 22/11/2026 : l'agenda Google. La clé de la délégation
Google Workspace de Bigup (data/google-agenda-delegation.json, 0600) sert l'agenda de nicolas@rossinienergy.com à la
place de celui de chaque compte du studio. Le studio n’y lit que les rendez-vous qu'il a créés, privés et marqués
disponibles (studio_platform.py). Retirer le fichier puis redémarrer le studio coupe l'agenda.

| Adresse | Ce que c'est |
|---|---|
| http://127.0.0.1:55813 | Bigup vu par Camille Martin, commerciale fictive, droits de base d'un commercial |
| http://127.0.0.1:55814 | Bigup vu par l'administrateur du studio (réglages seulement, jamais filmé) |

## Démarrer, arrêter, semer

    ./start.sh          # Postgres, migration de la plateforme, Drive du studio, plateforme, Site, relais, score
    seed/all.sh         # entreprises, secteurs de tournée, HubSpot de test, case Prospects (25)
    data/venv/bin/python seed/seed_shared_table.py   # Tableur partagé : la liste des stations de ski (475 lignes)
    data/venv/bin/python seed/seed_quick_contact.py  # une recherche de contact terminée (Prospection › Un contact)
    ./score.sh          # clients gagnés (portail de test) puis passage de score, relançable à la main
    ./stop.sh

Pour filmer « Sur la route », démarrer Docker Desktop, lancer `./routing.sh` puis redémarrer le studio.
Valhalla 3.9.1 calcule sur le poste avec les extraits OpenStreetMap Nord-Pas-de-Calais et Picardie
(Geofabrik). Son port 55816 est limité à la boucle locale. Le graphe reste dans le volume Docker
`bigup-studio-valhalla-data`. Régler l’agence de départ du profil de démonstration dans le studio.

Mettre le studio au code en production : data/site au commit de la dernière version Sites publiée (journal de
publication), puis npm --prefix data/site run build ; data/platform au commit de l'image leadgenerator-platform de
l'API en production (docker ps sur contabo-leadgen) ; puis ./stop.sh et ./start.sh. start.sh applique le schéma de
la plateforme (service provision, comme deploy.sh) et score.sh recalcule le score de chaque prospect : depuis le
21/11/2026, seul le serveur le calcule (row_scores), d'après les clients gagnés qu'il lit dans HubSpot.

Le contrôle avant tournage : `node ../../scripts/studio_check.mjs <scenario.json> <sortie>` (règle 6 du studio).

## Ajouts du 27/11/2026 (commande ord_62b82c366f10bf7a32a0, prospection v1073)

- `lockf -k data/tournage.lock ./update.sh <commit du Site> <commit de la plateforme>` met le studio au code en
  production et le relance (uv pour la plateforme, npm ci et build pour le Site).
- Demandes d'email et de téléphone : `studio_enrichment.py` fait tourner l'ouvrier de production avec un Enrow et un
  FullEnrich de test (clé factice `studio-double`, email sur example.fr, numéro de la plage 06 39 98 réservée à la
  fiction) ; `seed/seed_enrichment.py` pose les connecteurs avec les champs et les tarifs de production.
- Routeur : `studio_routing.py` (port 55817) transmet à Valhalla et n'estime à vol d'oiseau que les trajets qui sortent
  du graphe Nord et Picardie (stations de ski de la liste partagée) ; start.sh le lance et y branche la plateforme.
- Transfert de fiche : interrupteur `vente.transfert_prospect` allumé pour tous (set_feature_switch) et collègue fictif
  Théo Marchand, chargé d'affaires avec sa zone Ardennes et Marne (`node seed/seed_colleague.mjs`).
- Prospect en or : `seed/seed_gold_prospect.py` crée aussi la table des clients de la recherche des relations
  (clients_table_id) et la ligne du client qui présente, lues par le code du 26/11.
- Parkings voisins de la fiche filmée : une proposition non tranchée laisse « Calcul… » dans le lecteur. Valider la
  proposition (save_row_parking, action confirm) puis compter les places avec
  `leadgenerator-platform-survey-parkings --campaign <livret>` et `LEADGENERATOR_PARKING_MODEL=data/models/parking-stalls-osm-v1.onnx`
  (modèle copié de la production, hors Git).
- `matrice-fonctions.md` : matrice commune des fonctions du commercial entre les vidéos Prospection et Tournées.
- Incident du 27/11 vers 01 h : la table des fichiers de macOS saturée (kern.num_vnodes = kern.maxvnodes) après un
  remplissage de la mémoire d'échange par le serveur VoiceStudio (36 Go) a bloqué l'ouverture des fichiers de
  Documents pendant 1 h 30 ; un Chrome orphelin d'une session tuée gardait aussi le verrou. Ne jamais tuer une session
  sous lockf sans tuer ses navigateurs.

## Ajouts du 27/11/2026, corrections de Nicolas (commande ord_3a6e447e3115df3dde8b)

- Collègues réels (exception de Nicolas pour cette vidéo : photos et noms de vrais collègues, prospects et contacts
  toujours fictifs). `data/team.json` (hors Git, 0600) : sub, e-mail du répertoire de l'équipe, prénom, nom, adresse
  de la photo Slack, départements de la zone de démonstration. `data/venv/bin/python seed/seed_team.py` pose les
  photos Slack par le code du serveur des photos de l'ERP (ao/photos.py), l'annuaire de l'équipe (ao_personnes) et la
  liste des propriétaires de `data/studio-owners.json` ; `node seed/seed_team.mjs` crée leurs comptes commerciaux et
  leurs zones (destinataires de « Transférer »). `node seed/seed_team.mjs --theo off|on` éteint ou rallume les livrets
  de Théo Marchand, le collègue fictif, pour qu'il ne figure pas parmi des collègues réels.
- Photos des collègues : start.sh pose `LEADGENERATOR_AO_SERVICE_URL` vers la plateforme du studio, qui sert
  `/ao-api/photos` avec ses propres fichiers (`LEADGENERATOR_AO_DATA=data/ao`).
- Chargé d'affaires du client d'un prospect en or : le propriétaire HubSpot ne peut pas être un vrai collègue dans le
  portail de test (l'ajouter lui enverrait une invitation). `studio_platform.py` complète donc l'annuaire des
  propriétaires et le propriétaire des entreprises listées dans `data/studio-owners.json`.
  `data/venv/bin/python seed/seed_gold_client.py` relie Dubois Promotion (client de TECOBAT) à une entreprise et à un
  contact fictif du portail de test, nomme Thibaut Gourlin son chargé d'affaires et remet à zéro les décisions de feu
  vert (relançable avant chaque tournage).
- Feu vert pendant un tournage : étape `{"action": "run", "cmd": ["node", "../../studios/bigup/seed/feu_vert.mjs"],
  "dispatch": "bigup:colleague-decision"}` ; Thibaut autorise l'appel avec l'action de Bigup, puis la fiche relit sa
  décision.
- Tournage sans saccade : `"slowMotion": 4` dans le scénario (page, minuteurs, animations et gestes quatre fois plus
  lents, journal ramené au temps réel) et le GPU du Mac pour Chrome sans écran (scripts/studio_record.mjs). Avant, le
  rendu logiciel livrait 4 à 10 images/s pendant un mouvement de carte. Nouveaux gestes : clic droit (`"button":
  "right"`), glisser d'un décalage (`"drag"` avec `"by"`), boîte englobante d'un survol (`"boxAll"`).

## Ajouts du 27/11/2026 au soir (commande ord_fd3fd5ca38edbe264faa, Tournées refaites sur la version en ligne)

- Filtres d'À caler « Leads entrants », « Projets » et « Partenaires » : `data/venv/bin/python seed/seed_tournees_filtres.py`
  ajoute l'étape « Lead entrant » au Pipeline Bornes et l'option « Partenaire » du statut de lead dans le portail de test,
  pose le code postal (lu dans l'adresse) des entreprises du portail, puis crée une transaction « Lead entrant » sans
  propriétaire, une transaction « Projet » et une entreprise « Partenaire » sur trois entreprises réelles du Nord tirées
  d'un livret de production (lecture seule), interlocuteurs fictifs. Relançable sans doublon. Leurs lignes restent
  « sans position » : la copie HubSpot du studio (Réglages › Qualité HubSpot) n'a placé aucune entreprise ; les filtres
  et leurs compteurs se filment, les lignes elles-mêmes non.
- Heure des journées de tournée : `data/studio-clock` (une date ISO, par exemple `2026-11-27T08:40:00+01:00`, la même
  que `scenario.now`) fait suivre cette heure au calcul des journées (route_planner.now, studio_platform.py). Sans elle,
  un passage ajouté le jour même après 18 h, heure réelle du poste, vidait la journée (« ne tient pas dans une journée de
  0 min »). Redémarrer le studio après l'avoir changée, puis recalculer les journées touchées (optimize_itinerary).
- Bigup garde dans la page des copies cachées des fiches voisines (vue « Planifier un rdv », fiches) : dans un scénario,
  viser le texte et les boutons de ces vues avec `>> visible=true`.
- « Mon calendrier » affiche « Aucun rendez-vous ce jour. » quand le jour du tournage n'a pas de rendez-vous : ne pas
  l'ouvrir ce jour-là (empty state refusé par studio_check).

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

## Ce que chaque tutoriel montre

Passages obligés : le scénario de tout tutoriel qui filme l'écran concerné les reprend, et le résumé final dit à
quel minutage chacun apparaît. Un passage impossible dans le studio se corrige dans le studio (semis, secteur),
jamais en le sautant.

### Tournées : les zones et les filtres d'abord

Nicolas, 21/11/2026 : « on doit voir qu'on peut cliquer de zone en zone sur la carte. L'objectif est qu'ils
comprennent tout de suite l'importance des filtres et des zones. »

- Version : Site au commit 92faf92 (Bigup v1041) ou plus récent, la première où un clic sur la carte ouvre une zone
  (#376 à #381). Un studio plus ancien se remet au commit déployé avant le contrôle des écrans.
- Premier chapitre des Tournées, dans la première minute passée sur cet écran : la carte de la semaine avec la zone
  ouverte en couleur et les entreprises des autres zones grisées. La voix dit pourquoi : on prospecte zone par zone,
  et la liste, les filtres et leurs compteurs sont ceux de la zone ouverte.
- De zone en zone sur la carte, au moins deux passages : la main sur une autre zone qui s'éclaire, le clic qui
  l'ouvre (les couleurs changent, puis la carte se déplace ; la liste, les filtres et les compteurs deviennent ceux
  de la nouvelle zone) ; une entreprise grisée cliquée qui ouvre sa zone ; un clic dans le gris, loin des zones, qui
  ramène la carte sans changer de zone ; « Toutes les zones », qui cadre toutes les zones du commercial.
- Les filtres : un filtre décoché puis recoché, la liste et la carte qui suivent, les compteurs lisibles (zoom de la
  caméra), et le rappel qu'un choix reste au passage suivant. Montrés tôt, avant la prise de rendez-vous.
- Studio : au moins deux zones de Camille (« Métropole lilloise » et la seconde du semis) avec des prospects et des
  comptes dans chacune, pour que la zone ouverte et la zone grisée soient toutes deux pleines à l'écran.

### Prospection et tableur

- `data/venv/bin/python seed/seed_gold_prospect.py <ligne de livret>` importe un fournisseur documenté dans le
  livret du studio. Le script lit la relation qualifiée et le logo, remplace les personnes et retire l’historique
  d’enrichissement payant. Pour rejouer la démonstration TECOBAT, utiliser la ligne
  `2f0ae9a1-11c0-433b-b166-809f7810b853`, puis `./score.sh`.
- `data/venv/bin/python seed/seed_book_hubspot.py <ligne du studio>` crée l’entreprise dans le portail de test et
  la rapproche par le SIRET sourcé. Le script vérifie le portail avant chaque écriture. Pour SI Group à Béthune,
  utiliser la ligne `48e5a82d-9db8-400e-b9e0-b8b172a28f36`.
- `data/venv/bin/python seed/seed_ski_operators.py` attache les preuves officielles et charge les logos des
  exploitants de Courchevel Le Praz et de La Flégère. Le fichier local `data/stations-noms-a-anonymiser.json`
  liste les noms relevés dans les textes publics et les contacts des fiches filmées. Le semis les remplace
  dans le studio. Les deux actions « Ajouter à mes prospects » peuvent ensuite être filmées avec leur confirmation.
