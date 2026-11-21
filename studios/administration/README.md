# Studio de tournage Administration

Ce studio local fait tourner les Sites [Administration](https://ad.rossinienergy.com)
et [Formation](https://learning.rossinienergy.com) pour filmer les droits des
membres et le changement de vue d’un outil à l’autre.

| Service | Révision utilisée pour la commande |
| --- | --- |
| Site Administration | Sites v52, `80c672052b9feba26ceb2550838a87e2e54aef95` |
| Site Formation | Sites v50, `872ff46544ed96a59b9f6c8a2b7fff6d5f7f4237` |
| API Rossini | `74b2f2b1132b1a3ad5ac07a9658402e581a28a80` |
| Accès CRM | Route du CRM au commit `d92fb9dd3ee6` et migration `016-rossini-acces-crm.sql`, sur PostgREST local |
| Accès Plane | Image `rossini-plane-backend:1.4.2-pages.6`, espace Plane `studio` |
| ClassroomIO | Image `sha256:41fefb67caae5e358afbf3671976d33c34ddac5687c5eb698d176a9c7f6942d8`, organisation `formation-studio` |

Les dossiers `data/admin`, `data/learning` et `data/platform` sont des
copies de travail des révisions du tableau. Les deux Sites sont construits
avec `node scripts/run-framework.mjs build`, et leurs migrations D1
s’appliquent avec Wrangler en mode local. Les conteneurs
`oscar-administration-{db,redis,postgrest,plane,classroom}` utilisent le
réseau Docker isolé du studio. Les ports publiés sont liés à `127.0.0.1`.
Le fichier `data/learning.json` configure le vrai moteur ClassroomIO local
avec une clé et un compte de service propres à ce studio.

Sur le poste de montage déjà préparé, lancer `./start.sh`. Il réutilise
les binaires PostgreSQL et l’environnement Python du studio Bigup, ainsi que son portail
développeur HubSpot de test, dont il vérifie le type. La base et les
identités d’Administration sont propres à ce studio. Les comptes filmés
utilisent le domaine réservé `example.com`. L’annuaire de photos local
montre les initiales.

Le scénario Playwright fournit `localNetwork.ports` pour
`ad.rossinienergy.com:55824` et `learning.rossinienergy.com:55825`, et
`localNetwork.spki` depuis `data/studio-spki.txt`. Le navigateur résout ces
deux noms vers la boucle locale et le relais leur présente le certificat
du studio. Les cookies de la vue membre restent séparés par origine.
Le compte administrateur ne vient que du relais local.

Le contrôle et le tournage se lancent avec `scripts/studio_check.mjs` et
`scripts/studio_record.mjs`. Remettre l’accès Formation du membre filmé
en « Lecture » avant chaque passe du scénario qui enregistre « Modification ».
