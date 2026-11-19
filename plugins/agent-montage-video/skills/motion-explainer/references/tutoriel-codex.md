# Montrer un agent Codex dans ses fichiers

Repères documentaires vérifiés le 11 novembre 2026. Revérifier l'interface et la
documentation officielle avant le tournage d'une nouvelle version.

## Objectif pédagogique

Le spectateur doit savoir associer son projet au dossier de l'agent, trouver la
fiche de poste, ouvrir une compétence et retrouver les résultats. Filmer ces
opérations sur les vrais fichiers, avec une capture autorisée de l'application.
Une explication graphique complète la démonstration ; elle ne la remplace pas.

## Distinctions à conserver

- `AGENTS.md` : mission, règles communes, conventions du projet, résultat attendu.
  Garder le fichier court et mettre les détails spécialisés dans les compétences.
  Le présenter comme notre fiche de poste, pas une obligation de tout agent IA.
- `.agents/skills/<nom>/SKILL.md` : compétence locale de notre exemple Codex.
  Ouvrir l'en-tête YAML `name` / `description`, puis les entrées, la méthode,
  les sorties et les contrôles. Une compétence est un dossier ; le fichier
  principal peut appeler des références, des scripts ou des actifs facultatifs.
- `input`, `output`, `work` : conventions choisies pour le métier. Les rôles
  doivent être expliqués dans les instructions. Montrer d'autres organisations
  lorsqu'elles aident à comprendre que ces noms ne sont pas imposés par Codex.
- Les sources sont des données ; elles ne sont pas automatiquement des instructions.
  Un fichier disponible n'est pas nécessairement chargé dans le contexte.
- Les instructions ne créent pas une permission ni une connexion à un outil.

## Réalisation

Montrer le dossier principal effectivement associé au projet. Ouvrir les fichiers,
pas seulement leurs icônes ; prévoir l'affichage des dossiers cachés pour `.agents`.
Relier chaque règle de rangement au dossier correspondant. Une référence de skill
doit être un vrai fichier accessible via un lien qui fonctionne.

Faire passer un document réel et autorisé de l'entrée au résultat ; conserver
les originaux si c'est la règle choisie. Distinguer compétence disponible,
instructions lues et action exécutée. Ne pas inventer la trace interne du modèle.
Tester aussi une demande sans la donnée nécessaire et montrer le diagnostic réel.

Ouvrir une nouvelle conversation pour vérifier la reprise des consignes. Éviter
de promettre qu'AGENTS.md est relu à chaque message ou qu'une correction est déjà
chargée dans une session en cours. Les instructions globales et locales peuvent
se cumuler : vérifier le périmètre du projet montré.

Ne pas attribuer à une preuve CLI les gestes d'une application non filmée. Si la
capture est indisponible, conserver cette étape comme asset requis, avec le
blocage exact. La procédure de tournage ne doit pas contourner un refus d'accès.

## Sources primaires

- https://learn.chatgpt.com/docs/agent-configuration/agents-md
- https://learn.chatgpt.com/docs/build-skills
- https://learn.chatgpt.com/docs/customization/overview
- https://learn.chatgpt.com/docs/projects#use-local-projects-for-folders-and-codebases
