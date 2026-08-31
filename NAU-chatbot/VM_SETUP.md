# Ubuntu VM setup

This is a reproducible baseline for a fresh Ubuntu 24.04 LTS GPU VM. Package repositories, signing keys, and driver compatibility are external and can change; compare these commands with current Docker and NVIDIA vendor instructions in the controlled deployment environment before executing them.

Nothing in this runbook was executed while the repository was created.

## 1. Provision and patch the host

Provision at least 8 vCPU, 32 GiB RAM (64 GiB preferred), 150 GiB SSD, and an NVIDIA GPU with 16 GiB VRAM (24 GiB preferred). Allocate additional disk for backups and model revisions.

```bash
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
sudo apt-get install -y ca-certificates curl git gnupg openssl rsync ufw ubuntu-drivers-common
sudo timedatectl set-timezone Africa/Tunis
```

Install the recommended NVIDIA host driver, reboot, and verify it. Schedule the reboot so it does not interrupt other workloads:

```bash
sudo ubuntu-drivers install
sudo reboot
```

After reconnecting:

```bash
nvidia-smi
```

The host driver must support the CUDA 12.4 user-space runtime used by the inference image.

## 2. Install Docker Engine and Compose v2

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME:-$VERSION_CODENAME} stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out and back in so group membership is refreshed. Docker group membership is root-equivalent; grant it only to deployment operators.

```bash
docker version
docker compose version
```

## 3. Install NVIDIA Container Toolkit

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Do not proceed until the container sees the GPU. A successful host `nvidia-smi` alone does not verify the Docker runtime.

## 4. Place the application

Use an institution-controlled repository URL and a reviewed release tag:

```bash
sudo install -d -o "$USER" -g "$USER" /opt/iit-academic-assistant
git clone REPLACE_WITH_REPOSITORY_URL /opt/iit-academic-assistant
cd /opt/iit-academic-assistant
git fetch --tags --prune
git checkout REPLACE_WITH_REVIEWED_RELEASE_TAG
git status --short
```

If the source is transferred as an archive instead, verify its published SHA-256 checksum before extracting it under `/opt/iit-academic-assistant`. Do not copy a developer `.env`, caches, model files, database dumps, or node/Python virtual environments into the repository.

## 5. Create production configuration

```bash
cd /opt/iit-academic-assistant
cp .env.example .env
chmod 600 .env
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 24
openssl rand -hex 24
```

Edit `.env`:

- replace every `REPLACE_*` value with an independent secret;
- set the public HTTPS URL/host/origin;
- retain loopback bind addresses;
- retain `SECURE_COOKIES=true`;
- retain `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`;
- use a URL-safe Redis password;
- choose a versioned `CHROMA_COLLECTION`.

Build only the backend first and generate the Argon2id hash:

```bash
docker compose build backend
docker compose run --rm --no-deps backend python -c "from getpass import getpass; from argon2 import PasswordHasher; print(PasswordHasher().hash(getpass('Admin password: ')))"
```

Paste the complete hash as the single-quoted `ADMIN_PASSWORD_HASH` value, then validate Compose without printing its expanded output:

```bash
docker compose config --quiet
```

## 6. Stage approved model artifacts

The production inference service cannot download models. Prepare the artifacts on a trusted connected staging system. The following example uses the pinned Hugging Face client in a temporary virtual environment; model access may require `huggingface-cli login` and institutional license approval:

```bash
python3 -m venv /tmp/iit-hf-tools
. /tmp/iit-hf-tools/bin/activate
python -m pip install --upgrade pip
python -m pip install huggingface_hub==0.28.1
sudo install -d -o "$USER" -g "$USER" /srv/iit-model-stage
export HF_HOME=/srv/iit-model-stage
huggingface-cli download ESPRIT-Group/ESPRIT-Derja-Qwen3-8B-v2 --local-dir /srv/iit-model-stage/esprit
huggingface-cli download Qwen/Qwen3-4B-Instruct-2507 --local-dir /srv/iit-model-stage/qwen
huggingface-cli download intfloat/multilingual-e5-base --local-dir /srv/iit-model-stage/multilingual-e5-base
huggingface-cli download cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 --local-dir /srv/iit-model-stage/mmarco-reranker
deactivate
```

If `/srv/iit-model-stage/esprit/adapter_config.json` exists, obtain and stage its exact base snapshot in the `HF_HOME` cache:

```bash
ESPRIT_BASE_MODEL=$(python3 -c "import json; print(json.load(open('/srv/iit-model-stage/esprit/adapter_config.json', encoding='utf-8'))['base_model_name_or_path'])")
HF_HOME=/srv/iit-model-stage /tmp/iit-hf-tools/bin/huggingface-cli download "$ESPRIT_BASE_MODEL"
```

Record a checksum manifest outside the staged tree:

```bash
find /srv/iit-model-stage -type f -print0 \
  | sort -z \
  | xargs -0 sha256sum \
  > /srv/iit-model-stage.sha256
chmod 600 /srv/iit-model-stage.sha256
```

When downloads occur on another machine, transfer both the tree and checksum manifest securely, then verify on the VM:

```bash
sha256sum --check /srv/iit-model-stage.sha256
```

Build the inference image and copy artifacts into its named volume:

```bash
cd /opt/iit-academic-assistant
docker compose build --pull inference
docker volume create iit_academic_model_data
docker compose run --rm --no-deps --user root \
  -v /srv/iit-model-stage:/source:ro \
  inference sh -c 'cp -a /source/. /models/huggingface/'
```

Set direct container paths in `.env`:

```dotenv
ESPRIT_MODEL_PATH=/models/huggingface/esprit
QWEN_MODEL_PATH=/models/huggingface/qwen
EMBED_MODEL_PATH=/models/huggingface/multilingual-e5-base
RERANK_MODEL_PATH=/models/huggingface/mmarco-reranker
```

Keep the original approved model tree off-volume for recovery. Docker volume contents alone are not a sufficient artifact archive.

## 7. Build and start the stack

```bash
cd /opt/iit-academic-assistant
docker compose build --pull backend rag-worker inference frontend
docker compose up -d postgres redis chroma
docker compose ps
docker compose run --rm --no-deps backend alembic upgrade head
docker compose run --rm --no-deps backend python -m app.commands.seed_academic
docker compose up -d inference
docker compose ps inference
docker compose logs --tail=200 inference
```

The migration and seed commands are deliberate one-shot steps; backend startup never applies them. Wait until inference reports healthy, then build the first Chroma projection before exposing the application:

```bash
docker compose up -d rag-worker
docker compose run --rm --no-deps backend python -m app.commands.reindex_rag
docker compose logs --tail=200 rag-worker
docker compose exec redis redis-cli LLEN iit:rag:jobs
docker compose exec redis redis-cli LLEN iit:rag:processing
docker compose exec redis redis-cli LLEN iit:rag:dead
docker compose up -d backend frontend
docker compose ps
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/health/ready
curl --fail http://127.0.0.1:8080/healthz
```

The queue and processing lengths must both reach zero; the dead-letter queue must remain zero before acceptance testing. If indexing fails, inspect worker/inference logs and use the documented retry or rebuild procedure in [RAG.md](RAG.md).

## 8. Configure host nginx and TLS

Install the host reverse proxy. Replace the domain and operator email before running Certbot:

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
export IIT_DOMAIN=assistant.example.edu
export IIT_ADMIN_EMAIL=admin@example.edu
```

Create `/etc/nginx/sites-available/iit-academic-assistant` with:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name assistant.example.edu;

    client_max_body_size 1m;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # This is the public trust boundary: discard client-supplied X-Forwarded-For.
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_read_timeout 120s;
    }
}
```

Enable and validate it:

```bash
sudo ln -s /etc/nginx/sites-available/iit-academic-assistant /etc/nginx/sites-enabled/iit-academic-assistant
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
sudo certbot --nginx --domain "$IIT_DOMAIN" --email "$IIT_ADMIN_EMAIL" --agree-tos --no-eff-email --redirect
sudo certbot renew --dry-run
```

The `rm` above targets only Ubuntu nginx's known default-site symlink; verify the exact path before executing it on a shared host. On a shared reverse proxy, preserve unrelated site definitions.

Update `.env` to the same HTTPS domain before accepting logins, then recreate backend/frontend if it changed:

```bash
docker compose up -d --force-recreate backend frontend
curl --fail "https://${IIT_DOMAIN}/healthz"
```

## 9. Firewall

Restrict SSH to the administration source range whenever possible:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

Do not open 5432, 6379, 8000, 8010, or Chroma externally. Compose binds 8000/8080 to loopback and does not publish the remaining service ports.

## 10. Reboot and acceptance

Docker is enabled and each service uses `restart: unless-stopped`. Reboot during the maintenance window and verify recovery:

```bash
sudo reboot
```

After reconnecting:

```bash
cd /opt/iit-academic-assistant
docker compose ps
nvidia-smi
curl --fail http://127.0.0.1:8000/health/ready
curl --fail http://127.0.0.1:8080/healthz
docker compose exec redis redis-cli LLEN iit:rag:jobs
docker compose exec redis redis-cli LLEN iit:rag:processing
docker compose exec redis redis-cli LLEN iit:rag:dead
```

Complete institutional acceptance before opening traffic:

- anonymous session create/chat/reset;
- Tunisian/Arabizi profile facts, negation, friend/family/hypothetical isolation;
- corrected Prépa MP and Math/Sciences-only eligibility;
- ineligible recommendation/CTA suppression;
- source-backed fees, curricula, careers, and EURO-INF/ASIIN wording;
- admin login/refresh/logout and CSRF failures;
- all seven CRUD screens, safe delete/deactivation, pagination/filtering;
- incremental and complete RAG indexing;
- concurrent same-session turns and idempotent retry;
- backup plus isolated restore rehearsal;
- load, latency, VRAM/RAM, restart, dependency outage, and security tests.

Follow [DEPLOYMENT.md](DEPLOYMENT.md) for backups, upgrades, rollback, and monitoring. The repository has not been installed, built, started, migrated, indexed, or tested by the implementation agent.
