# Construire le studio d'un outil de l'ERP

Un studio, ce sont des services locaux sur le poste de montage et un jeu de vitrine, gardés dans `studios/<outil>/` :
scripts versionnés, données et secrets dans `studios/<outil>/data/` (hors Git). Modèle complet : `studios/bigup`.

| Pièce | En local (exemple Bigup) |
|---|---|
| Base | Postgres natif du studio (micromamba, `data/pg`, port 55810) : Docker n'est pas requis |
| Plateforme | le paquet du dépôt de l'outil au commit en production, lancé par `studio_platform.py` (port 55811) |
| Site | le Site au commit publié, `npm run build`, wrangler dev local (port 55812), base D1 locale migrée |
| Relais d'identité | `relay.mjs` : pose les en-têtes ChatGPT d'un compte fictif (commercial 55813, administrateur 55814) |
| HubSpot | un portail de test développeur (gratuit, `DEVELOPER_TEST`), jamais le portail de Rossini (6053297) |
| Google Drive | `drive_double.py` (port 55815) : instantané en lecture seule du vrai Drive partagé, lu par le connecteur Google Drive |

`start.sh` démarre tout, chaque service dans sa propre session (il survit au terminal), vérifie le portail HubSpot
et refuse de démarrer sur un autre portail qu'un compte de test ; `stop.sh` arrête tout.

## Identité sans ChatGPT

En production, ChatGPT Sites pose `oai-authenticated-user-id`, `-email` et `-full-name` ; le Site signe ses appels
à la plateforme avec `LEADGENERATOR_GATEWAY_SECRET`. Au studio, le relais pose ces en-têtes pour un compte fictif et
`seed/call.mjs` signe les appels de semis avec le secret du studio (48 caractères tirés au hasard).

## Compte de démonstration

Un collègue fictif du rôle (Bigup : Camille Martin, commerciale), réglé comme les collègues de ce rôle en production :
lire en lecture seule le réglage le plus courant (Bigup : Tournées et « Enrichissement · Un contact » en écriture,
comme 11 commerciaux sur 17) et l'appliquer par l'outil d'administration de l'outil. Zone, agence et secteurs de
tournée réglés comme un commercial bien installé.

## Jeu de vitrine

- Entreprises réelles : échantillon tiré au hasard dans un livret de production, en lecture seule (transaction read
  only, par SSH) : ligne, réponses sourcées, parking, cadastre, score, logo (fichiers copiés).
- Personnes fictives : chaque vraie personne est remplacée partout par le même double fictif, sans accents ni casse
  oubliés (« Prénom Nom », « NOM Prénom », first_name/last_name, identifiant de profil), en gardant la structure des
  réponses pour que le score reste celui de la production. Les noms d'entreprise sont protégés (« ETABLISSEMENTS GUY
  MARIN » reste la société). E-mails nominatifs en `@example.fr`, mobiles en `01 99 00 …`, profils LinkedIn fictifs,
  liens HubSpot retirés, notes d'appel et décisions internes vidées. Le semis échoue si une seule vraie personne reste.
- HubSpot de test : propriétaire fictif sans e-mail d'invitation, pipelines de Rossini, entreprises réelles avec
  interlocuteurs fictifs, transactions en cours et rendez-vous fictifs de la semaine.
- Volumes de la production : Bigup montre 25 prospects (au plus 21 verts selon la note calculée par le navigateur,
  le reste en ajouts manuels « Ajouté par moi »). `seed_finish.py` le vérifie en ouvrant l'accueil.

Ordre : `seed/all.sh` (entreprises, secteurs, HubSpot de test, case Prospects). Le semis refuse de tourner si une
variable d'un service extérieur est présente dans son environnement.

## Avant un tournage

Revenir au commit déployé du Site et de la plateforme, reconstruire, relancer, rejouer le semis si le schéma a
changé, rafraîchir l'instantané du Drive, puis `node scripts/studio_check.mjs` sur le scénario : aucun écran ne doit
montrer d'erreur, de réglage manquant, d'état vide ou de chargement sans fin (règle 6 du studio). Un studio qui ne
démarre pas s'arrête avec l'erreur exacte : on ne filme pas une autre version.

