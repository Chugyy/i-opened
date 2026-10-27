# Seconde instance i-opened pour HTR (preparation, NON deployee)

Decision (etude H5) : une **seconde instance** (base et projet separes), pas de multi-tenant. Meme image ghcr que la prod Multimodal ; isolement total des donnees.

## Pre-requis
- Cette PR (`hotfix/failles-second-client`) mergee **et** la prod Multimodal redeployee avec le correctif, avant toute donnee HTR reelle.
- Aucun secret dans ce depot : les valeurs vont dans Dokploy (onglet Environment) ou dans un profil `packages/<outil>/.profiles/`.

## Nommage propose
| Element | Valeur |
|---|---|
| Projet Dokploy | `I-Opened-HTR` (nouveau projet, ne pas reutiliser `I-Opened`) |
| Services | `htr-backend`, `htr-frontend`, base `htr-postgres` |
| Base / utilisateur | `iopened_htr` / `iopened_htr` |
| Front (a confirmer avec Julien) | `rdv.<domaine-htr>` si hebergement HTR, sinon `htr.i-opened.multimodal-house.fr` |
| API | `api-htr.i-opened.multimodal-house.fr` (ou `api.rdv.<domaine-htr>`) |

## Variables d'environnement
Backend (`config/config.py`) :
| Variable | Valeur |
|---|---|
| `PRODUCTION` | `true` |
| `DEBUG` | `false` |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | service postgres HTR, base `iopened_htr`, mot de passe genere (>= 24 car.) |
| `JWT_SECRET_KEY` | secret aleatoire **propre a HTR** (`openssl rand -hex 32`), jamais celui de la prod Multimodal |
| `SETUP_SECRET` | secret d'installation aleatoire ; sert une seule fois pour creer l'admin, puis `/auth/setup` reste ferme de toute facon (un utilisateur existe) |
| `FRONTEND_URL` | URL publique du front HTR |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` | client OAuth Google dedie HTR, redirect sur l'API HTR |
| `SMTP_*`, `UNIPILE_DSN` (+ cle), `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | uniquement si les relances HTR sont voulues |
Frontend : `NEXT_PUBLIC_API_URL` = URL publique de l'API HTR (variable de build : rebuild de l'image si elle change).

## Checklist de deploiement Dokploy (Dedibox, `100.91.248.86:3000`)
1. Dokploy : creer le projet `I-Opened-HTR` ; ajouter un service PostgreSQL (`htr-postgres`), volume persistant.
2. Appliquer les migrations `backend/app/database/migrations/*.sql` dans l'ordre (001, 002, 003 x2) sur `iopened_htr`.
3. Creer `htr-backend` et `htr-frontend` sur les images ghcr (`ghcr-dedibox`), tag `:<sha>` du commit mergé (pas `:latest`).
4. Renseigner les variables ci-dessus ; healthcheck backend `/health` (port 8000).
5. Domaines + TLS (DNS vers la Dedibox) ; verifier le CORS/`FRONTEND_URL`.
6. Creer l'admin HTR **une seule fois** : `curl -X POST <api>/api/auth/setup -H "X-Setup-Secret: <secret>" -H "Content-Type: application/json" -d '{"email":..,"password":..,"fullName":..}'`. Le formulaire `/setup` du front n'envoie pas l'en-tete : avec `SETUP_SECRET` defini, il est refuse (voulu). Stocker les identifiants dans un profil, pas dans un fichier.
7. Preuves : `GET /health` 200 ; second `POST /api/auth/setup` => 403/409 ; `GET /api/leads` sans token => 401/403 ; `/book/<slug>` public => 200.
8. Ne pas brancher le CI de ce depot sur la seconde instance sans decision (le deploy.yml actuel declenche la prod Multimodal).

## Import des RDV iClosed (non code, a construire)
- Source : API iClosed documentee (`packages/iclosed/README.md`), cle dans le profil `iclosed` (fournie par HTR).
- `GET /v1/eventCalls` (`limit` <= 100, `page` base 0, filtres `dateFrom`/`dateTo`, `outcomes`, `userIds`, `setterIds`) et `GET /v1/contacts` ; la reponse `eventCalls` est en HTTP 201, forme `{data:{eventCalls:[...],count:N}}`.
- Quota 20 a 100 requetes / 10 s : pagination avec pause.
- Mapping : contact -> `leads` (email + calendrier), eventCall -> `bookings` (starts_at/ends_at, statut : annule -> `cancelled`, no show -> `no_show`, sinon `confirmed`), questionnaire (`secondaryAnswers`) -> `leads.answers`.
- Rejouable : ajouter une colonne `external_id` (iClosed) avec index unique sur `leads` et `bookings` (migration 004) et faire des upserts.
- Prealable : le pipeline closing (resultat d'appel, montant, closers) n'existe pas encore ; l'import doit d'abord conserver `outcome`/`closer` dans un champ JSON ou des colonnes dediees.
