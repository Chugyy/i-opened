# Deploiement continu (prod I-Opened sur la Dedibox)

Chaque push sur `main` lance `.github/workflows/deploy.yml` :

1. `build-backend` / `build-frontend` (runners GitHub) : images poussees sur GHCR,
   tags `latest` et `<sha>`.
2. `deploy` (runner auto-heberge `[self-hosted, dedibox]`) : appelle l'API Dokploy
   locale de la Dedibox (`localhost:3000`, jamais exposee publiquement) via
   `.github/scripts/dokploy-deploy.sh`, `application.deploy` pour le backend puis le
   frontend du projet Dokploy `I-Opened`. Le job attend que le deploiement passe a
   `done` et echoue si l'API refuse, si le deploiement finit en `error` ou apres 10 min.

## Runner

- Service systemd `actions.runner.Chugyy-i-opened.dedibox`, installe dans
  `/opt/actions-runner`, utilisateur systeme `gh-runner` (non root, sans sudo, hors du
  groupe `docker`) : il n'a besoin que de l'API Dokploy.
- Enregistre sur ce seul depot, labels `self-hosted,dedibox`.
- Reenregistrer : `gh api -X POST repos/Chugyy/i-opened/actions/runners/registration-token`
  puis `config.sh --url https://github.com/Chugyy/i-opened --token <token> --labels dedibox --replace`
  en `gh-runner`.

## Securite (depot public)

Un runner auto-heberge sur un depot public peut executer le code d'un fork. Garde-fous :

- le job `deploy` ne tourne que pour `push` sur `main` ou `workflow_dispatch` (reserve aux
  collaborateurs) ; jamais de trigger `pull_request` dans ce workflow ;
- environnement GitHub `production` limite a la branche `main`, qui porte les secrets
  `DOKPLOY_URL`, `DOKPLOY_API_KEY`, `DOKPLOY_BACKEND_ID`, `DOKPLOY_FRONTEND_ID` ;
- reglage du depot : les workflows des PR de forks exigent une approbation pour tout
  contributeur externe (`fork-pr-contributor-approval = all_external_contributors`).
  GitHub ne permet pas de les desactiver totalement sur un depot public : ne jamais
  approuver un run de fork qui modifie `.github/`.
