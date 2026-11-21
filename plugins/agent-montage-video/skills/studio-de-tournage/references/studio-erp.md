# Construire le studio d'un outil de l'ERP

Un studio = trois services locaux sur le poste de montage, plus un jeu de données de vitrine. Il se construit une
fois par outil, dans `studios/<outil>/`, et se met à jour au commit déployé avant chaque tournage.

| Pièce | D'où elle vient | En local |
|---|---|---|
| Site de l'outil | dépôt du Site (ex. leadgenerator-site), commit publié | `npm ci`, `npm run build`, `npm start` (wrangler dev local) ; variables dans `.dev.vars` |
| Serveur de plateforme | dépôt sales-marketplace, commit en production | `leadgenerator-platform` (point d'entrée de l'image), base Postgres du studio |
| Base | conteneur Docker Postgres dédié au studio | schéma créé par la plateforme, puis jeu de vitrine |
| Relais d'identité | script du studio | pose les en-têtes du compte de démonstration |

## Identité sans ChatGPT

En production, ChatGPT Sites pose `oai-authenticated-user-id`, `oai-authenticated-user-email` et
`oai-authenticated-user-full-name` ; le Site les lit (`authenticatedActor`, lib/platform-service.mjs) et signe
ses appels à la plateforme avec `LEADGENERATOR_GATEWAY_SECRET`. Au studio, un relais local devant `npm start` pose
ces en-têtes pour le compte de démonstration. Le scénario peut aussi les passer (`headers`). Aucun compte ChatGPT
de plus.

## Variables

Site (`.dev.vars`) : `LEADGENERATOR_SERVICE_URL=http://127.0.0.1:<port>` (le Site n'accepte le http qu'en
127.0.0.1 ou localhost), `LEADGENERATOR_GATEWAY_SECRET` (48 caractères tirés au hasard pour le studio),
`LEADGENERATOR_WORKSPACE_ID` et `LEADGENERATOR_SITE_ID` du studio. Plateforme : `LEADGENERATOR_DATABASE_URL` (base
du studio), le même secret, le même espace et site, `LEADGENERATOR_ADMIN_SUBJECT` d'un administrateur fictif.
Rien d'autre : toute variable d'un service extérieur reste vide, pour que la règle 4 tienne.

## Jeu de vitrine

- Lire un échantillon d'entreprises en production, en lecture seule, par SSH sur le serveur de l'outil : champs
  publics seulement (identité, adresse, logo et ses sources, score, parking et cadastre, réponses sourcées).
  Jamais les personnes, les échanges, les comptes connectés ni la configuration.
- Créer les personnes, rendez-vous, tournées et échanges en données fictives cohérentes (prénoms français
  courants, domaines `example.fr`, numéros `01 99 00 xx xx`).
- Régler les accès du compte de démonstration comme pour un collègue du rôle (Administration de l'outil), et
  vérifier en l'ouvrant que le menu est celui de ce rôle.
- Le script de semis vit dans `studios/<outil>/seed` ; il refuse de tourner si une variable de production est
  présente dans son environnement.

## Mise à jour avant un tournage

Revenir au commit déployé du Site et de la plateforme, reconstruire, relancer, rejouer le semis si le schéma a
changé, puis refaire la vérification `work/studio-check.md`. Un studio qui ne démarre pas s'arrête avec l'erreur
exacte : on ne filme pas une autre version.
