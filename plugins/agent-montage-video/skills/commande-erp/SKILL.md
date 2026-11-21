---
name: commande-erp
description: Exécuter une commande vidéo passée par un agent de l'ERP Rossini (Apolline en Formation, Margaux aux Appels d'offres) sur le poste de montage ou sur l'ordinateur de la personne - lire le bon de commande, appliquer les valeurs par défaut, donner l'avancement, poser au plus une série de questions bloquantes à la personne, publier, puis rendre une fin mesurée et vérifiée. Utiliser dès qu'un dossier projects/commande-<id>/ existe, qu'on parle d'une commande d'agent, d'un bon de commande vidéo ou du poste de montage.
---

# Exécuter une commande de l'ERP

Les agents de l'ERP Rossini ne se parlent pas : ils se passent des commandes écrites (règle rossini-erp 1.20.0,
`agent-orders.md`, critère A25). Un bon de commande vidéo a été rempli par l'agent responsable d'un espace et validé
par la personne. Tu l'exécutes ici, avec les outils de ce dépôt, et tu ne reçois que son paquet.

## Où est la commande

- **Poste de montage** (service `scripts/agent_host.py serve`) : `projects/commande-<id>/order.json`, sources dans
  `sources/`, travail dans `work/` et `out/`. Les comptes rendus passent par `python3 scripts/agent_host.py report …`
  lancé avec `AGENT_HOST_ORDER_DIR` (déjà réglé par le service).
- **Ordinateur de la personne** (commande « own ») : le plugin de l'agent prend la commande avec l'outil
  `work_agent_order` de l'ERP (`op: claim`, puis `source`, `progress`, `ask`, `finish`, `fail` avec le bail reçu). Avant
  de commencer, dire à la personne combien de temps le travail prendra et de laisser l'ordinateur allumé et branché,
  Codex ouvert, capot ouvert (l'écran peut se verrouiller) ; lancer chaque commande longue avec `caffeinate -i -s`.
  Avant de prendre la commande, vérifier qu'il reste au moins 20 Go libres sur le disque du dépôt (`df -h .`) : un
  rendu 4K qui remplit le disque s'arrête en route (19/11/2026). Sinon, ne pas la prendre et dire à la personne
  combien de place libérer ; la commande attend en file.

## Procédure

- [ ] Lire tout `order.json` : `brief` (but, public, durée, format, style, voix, sources, décisions, critères),
      `defaults` (les champs que la personne n'a pas donnés), `instructions` et `skills` (consignes et skills d'Oscar
      pour l'espace), `answers` et `checkpoint` s'il s'agit d'une reprise.
- [ ] Appliquer chaque valeur par défaut sans la demander, et la citer dans le résumé final.
- [ ] Faire la vidéo selon l'AGENTS.md du dépôt (voix VoiceStudio, rendu par tranches, 4K) et le style demandé
      (`styles/<style>/README.md`). Vidéo pédagogique : skill `motion-explainer`, et `meet-video-pedagogique` pour une
      réunion enregistrée. Appels d'offres : le skill d'Oscar transmis dans `order.json` et `kits/ao-essentiel`.
      Tutoriel d'un outil de l'ERP (`brief.interface`) : skill `studio-de-tournage`.
- [ ] À chaque étape : `report progress --step "…" --percent N --eta <secondes>`, avec `--checkpoint
      work/checkpoint.json` (étapes faites, tranches rendues) et une image d'aperçu (`--preview`) quand elle existe.
- [ ] Publier la vidéo vérifiée : `scripts/with_secrets.sh python3 scripts/publish_mux.py --video out/<film>.mp4
      --title "<titre du bon>" --metadata-output out/<film>.mux.json` (la personne a accepté la publication Mux en
      validant le bon).
      Compte Mux plein (« Free plan is limited to 10 assets ») : ne pas échouer. Nicolas a demandé de retirer les
      anciennes versions (21/11/2026). Lister les vidéos Mux ; une **ancienne version** est une vidéo remplacée par une
      plus récente du même sujet (titre en v1 quand une v2 existe, premier jet remplacé par sa version définitive).
      Avant de la retirer, chercher son identifiant de lecture dans les leçons (base ClassroomIO, tables `block`) et dans
      les dossiers d'appels d'offres (bases de la vente et de l'AO) : utilisée nulle part, la retirer (suppression
      définitive, notée dans le résumé avec son titre) puis publier. Aucune ancienne version libre : `report fail` avec
      la liste des vidéos et ce qu'il faut décider.
- [ ] Terminer : `report finish --video out/<film>.mp4 --mux out/<film>.mux.json --subtitles work/<film>.srt --summary
      "…"` et un `--check <id>="mesure"` par critère ajouté au bon. Le script mesure lui-même durée et résolution
      (ffprobe), vérifie la vidéo image par image (`video-frame-review`) et lit le lien Mux ; le serveur confronte ces
      mesures au bon. S'il refuse, corriger et recommencer.

## Premier jet et version définitive

- `brief.voice` vaut `voicestudio` par défaut : c'est le **premier jet**, voix gratuite et locale. Le résumé le dit
  (« premier jet en voix VoiceStudio ») ; l'agent qui a commandé proposera ensuite la voix définitive à la personne.
  Tu rends la vidéo à cet agent (Apolline, Margaux), cheffe de projet, jamais directement à la personne : le serveur
  la prévient en son nom une fois qu'elle a repris le résultat.
- `brief.revision_of` = `ord_…` : **version définitive** d'une commande livrée. Reprendre
  `projects/commande-<revision_of>/` (scénario, tournage `work/rec`, caméra, montage, style) dans le dossier de cette
  commande ; ne refaire que ce que le bon change. Voix ElevenLabs (`brief.voice` = `elevenlabs`, payante, acceptée
  par la personne sur la carte du bon) avec le skill `voice-intonation` (Eleven v3, meilleure prise sur plusieurs,
  mesure de l'intonation), clé par `scripts/with_secrets.sh`. Recaler gestes, sous-titres et caméra sur la nouvelle
  voix, rendre, vérifier image par image, publier sur Mux. Le premier jet reste sur Mux : l'agent qui a commandé le
  remplace dans sa leçon ; ne le supprimer que lorsqu'aucune leçon ne l'utilise.
- Le dossier du premier jet manque (autre poste, nettoyé) : `report fail` avec cette raison exacte ; ne jamais
  retourner une vidéo pour éviter l'échec sans le dire.

## Questions : une seule série, à la personne

Aucune question à un autre agent, jamais. Une décision qu'aucune valeur par défaut ne règle et qui change la vidéo
(une personne à montrer, une information absente de toutes les sources) devient une question fermée : écrire
`work/questions.json` (`[{text, why, choices}]`, cinq au plus, deux à cinq choix chacune), lancer `report ask
--questions work/questions.json` et s'arrêter. La commande reprend avec les réponses (`answers`). Une deuxième série
est refusée : appliquer alors l'hypothèse la plus prudente et la citer dans le résumé.

## Contrôles avant de rendre le résultat

1. La vidéo fait la durée visée à 15 % près, dans la résolution du format (3840 × 2160 en 4K 16:9).
2. Les sous-titres existent (fichier SRT avec ses répliques).
3. La vérification image par image ne trouve aucune image isolée.
4. Chaque fait montré vient d'une source du bon ; rien n'est inventé.
5. Chaque critère ajouté au bon a sa mesure.

## Cas d'échec

- Une source manque ou ne se lit pas, VoiceStudio ou le rendu échouent sans solution : `report fail --error "raison
  exacte et ce qu'il faut faire"`. Ne jamais livrer une vidéo partielle ni présenter un travail comme fini.
- Le serveur répond `lease_mismatch` : la commande a été annulée ou reprise ailleurs ; arrêter le travail.
