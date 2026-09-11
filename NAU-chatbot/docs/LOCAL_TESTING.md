# Tests sur la VM, hors Docker

Les services locaux utilisent les binaires installés dans `.runtime/`, les environnements Python du dossier `backend/` et la configuration privée `.env`.

```bash
bash scripts/local-start.sh
bash scripts/local-status.sh
```

Le frontend compilé écoute sur **8080** et relaie `/api` vers le backend sur `127.0.0.1:8000`. Transférer uniquement le port 8080 pour tester avec le tunnel configuré dans `PUBLIC_BASE_URL`. Les cookies de connexion sont sécurisés : utiliser l'URL **HTTPS** du tunnel pour tester la connexion et le renouvellement de session.

Les services sont conservés dans des sessions tmux après fermeture du terminal. Pour les arrêter :

```bash
bash scripts/local-stop.sh
```

Les journaux se trouvent dans `.runtime/logs/`. Un retour non nul de `local-status.sh` indique qu'un service est absent ou pas encore prêt. Le chargement initial des modèles peut prendre plusieurs minutes. Les téléchargements Hugging Face doivent être terminés avant de démarrer les processus d'inférence, qui fonctionnent ensuite en mode local uniquement.

## Données

La base locale `iit_academic` a été initialisée avec `iit_repository_seed.sql`, le snapshot académique du dépôt. Ce fichier restaure également le schéma et la version Alembic. **Ne pas le réimporter sur une base modifiée sans sauvegarde** : il recrée les objets de l'application.

La voie Alembic + `python -m app.commands.seed_academic` charge le catalogue YAML ; son contenu diffère du snapshot SQL. Elle a été vérifiée séparément sur une base temporaire, avec deux exécutions successives du seed.

Chroma se reconstruit depuis PostgreSQL. Une fois l'inférence prête :

```bash
PYTHONPATH=backend backend/.venv/bin/python -m app.commands.reindex_rag
```

## Vérifications du code

```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q
PATH="$PWD/.runtime/node/bin:$PATH" npm --prefix frontend test
PATH="$PWD/.runtime/node/bin:$PATH" npm --prefix frontend run build
```

Après une modification du frontend, reconstruire les fichiers puis redémarrer sa session :

```bash
tmux kill-session -t nau-frontend
bash scripts/local-start.sh
```

Les dépendances, modèles et données d'exécution sont ignorés par Git. Une nouvelle copie du dépôt sur une autre machine exige leur installation ; seuls les fichiers sources et les seeds sont versionnés.
