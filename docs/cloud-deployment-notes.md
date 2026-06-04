# Cloud Deployment Learning Notes

Project: Secure Enterprise RAG Chatbot / Codemars Intranet

This document records the cloud deployment learning path from Docker setup to
AWS EC2 deployment preparation.

---

## 1. Why Docker Is Needed

Docker packages an application with the runtime it needs.

For this project:

- Backend needs Python, FastAPI, dependencies, backend code, and Uvicorn.
- Frontend needs Vue build files served by nginx.
- Docker lets the same application run locally, in CI, and in cloud.

Key terms:

- **Dockerfile**: recipe for building one Docker image.
- **Image**: packaged application template.
- **Container**: running instance of an image.
- **Docker Compose**: runs multiple containers together.
- **Volume**: persistent Docker storage.
- **Registry**: place to store Docker images, such as AWS ECR.

---

## 2. Backend Dockerfile

File:

```text
backend/Dockerfile
```

Final content:

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt

RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Explanation:

- `FROM python:3.12-slim`: uses official Python 3.12 slim Linux image.
- `PYTHONDONTWRITEBYTECODE=1`: prevents `.pyc` cache files.
- `PYTHONUNBUFFERED=1`: prints logs immediately.
- `PYTHONPATH=/app`: allows imports like `backend.main`.
- `WORKDIR /app`: all later commands run from `/app`.
- `apt-get install build-essential`: installs Linux build tools for Python packages.
- `COPY backend/requirements.txt ...`: copies dependency file first for Docker cache.
- `pip install ...`: installs backend dependencies.
- `COPY backend ...`: copies backend code and data.
- `EXPOSE 8000`: documents backend port.
- `CMD ... --host 0.0.0.0`: starts FastAPI and makes it reachable from outside the container.

Build command:

```powershell
docker build --file backend/Dockerfile --tag codemars-rag-backend .
```

Run command:

```powershell
docker run --rm -p 8000:8000 codemars-rag-backend
```

Test:

```text
http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

---

## 3. Docker Ignore

File:

```text
.dockerignore
```

Purpose:

Docker sends the project folder as build context. `.dockerignore` prevents
unnecessary or secret files from being sent.

Recommended content:

```dockerignore
.git/
.venv/
venv/

__pycache__/
*.py[cod]

frontend/node_modules/
frontend/dist/

backend/logs/
.env
*.log
```

Why:

- avoids copying local virtual environments
- avoids copying `node_modules`
- avoids copying logs and secrets
- makes Docker builds faster and safer

---

## 4. Frontend Dockerfile

File:

```text
frontend/Dockerfile
```

Final content:

```dockerfile
FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package*.json ./

RUN npm ci

COPY frontend ./

RUN npm run build

FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
```

Explanation:

- This is a **multi-stage build**.
- Stage 1 uses Node to build Vue.
- Stage 2 uses nginx to serve static files.
- Final image does not need Node or `node_modules`.

Build command:

```powershell
docker build --file frontend/Dockerfile --tag codemars-rag-frontend .
```

Run command:

```powershell
docker run --rm -p 5173:80 codemars-rag-frontend
```

Test:

```text
http://localhost:5173
```

---

## 5. nginx Config

File:

```text
frontend/nginx.conf
```

Final content:

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Why nginx is needed:

- serves Vue static files
- forwards `/api/*` requests to backend
- supports Vue single-page app fallback

Important proxy behavior:

```text
/api/health -> backend:8000/health
/api/chat   -> backend:8000/chat
```

The slash in this line matters:

```nginx
proxy_pass http://backend:8000/;
```

---

## 6. Docker Compose

File:

```text
docker-compose.yml
```

Purpose:

Runs backend and frontend together.

Example final structure:

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: codemars-rag-backend
    environment:
      LLM_PROVIDER: ${LLM_PROVIDER:-fake}
      GROQ_API_KEY: ${GROQ_API_KEY:-}
      GROQ_MODEL: ${GROQ_MODEL:-llama-3.1-8b-instant}
      EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER:-hash}
      RAG_LOG_DIR: /app/backend/logs
    ports:
      - "8000:8000"
    volumes:
      - backend_logs:/app/backend/logs
      - chroma_data:/tmp/secure_rag_chroma_api
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    container_name: codemars-rag-frontend
    depends_on:
      backend:
        condition: service_healthy
    ports:
      - "5173:80"

volumes:
  backend_logs:
  chroma_data:
```

Run:

```powershell
docker compose up --build
```

Test:

```text
http://localhost:5173
http://localhost:5173/api/health
```

Expected API health:

```json
{"status":"ok"}
```

Stop:

```powershell
docker compose down
```

Stop and delete volumes:

```powershell
docker compose down -v
```

---

## 7. Environment Variables

Files:

```text
.env.example
.env
```

`.env.example` is safe to commit.

```env
LLM_PROVIDER=fake
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant
EMBEDDING_PROVIDER=hash
```

`.env` is local/private and should not be committed.

Why:

- secrets should not be hardcoded
- cloud platforms inject environment variables
- GitHub Actions can use secrets later

Check Compose config:

```powershell
docker compose config
```

---

## 8. Docker Volumes

Volumes used:

```yaml
backend_logs:/app/backend/logs
chroma_data:/tmp/secure_rag_chroma_api
```

Purpose:

- `backend_logs`: stores monitoring logs
- `chroma_data`: stores Chroma vector DB files

View volumes:

```powershell
docker volume ls
```

Enter backend container:

```powershell
docker compose exec backend sh
```

Check logs:

```sh
ls /app/backend/logs
cat /app/backend/logs/chat_events.jsonl
```

JSONL means one JSON object per line.

---

## 9. GitHub Actions CI

File:

```text
.github/workflows/ci.yml
```

Purpose:

Run checks automatically on GitHub.

The CI pipeline checks:

- backend tests
- RAG evaluation
- frontend build
- backend Docker image build
- frontend Docker image build

Core workflow:

```yaml
name: CI

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install backend dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt

      - name: Run backend tests
        run: python -m unittest discover backend/tests -v

      - name: Run RAG evaluation
        run: python -m backend.evaluation.run_eval

  frontend-build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install frontend dependencies
        working-directory: frontend
        run: npm ci

      - name: Build frontend
        working-directory: frontend
        run: npm run build

  docker-build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build backend Docker image
        run: docker build --file backend/Dockerfile --tag codemars-rag-backend .

      - name: Build frontend Docker image
        run: docker build --file frontend/Dockerfile --tag codemars-rag-frontend .
```

Important lesson:

CI starts from repo root, so backend requirements path must be:

```text
backend/requirements.txt
```

not:

```text
requirements.txt
```

---

## 10. AWS IAM User

Created IAM user:

```text
rag-chatbot
```

Purpose:

Use AWS CLI from local PowerShell.

Policies for learning:

```text
AmazonEC2FullAccess
AmazonEC2ContainerRegistryPowerUser
```

Why:

- EC2 policy allows managing EC2 servers.
- ECR policy allows creating repositories and pushing Docker images.

Configure AWS CLI:

```powershell
aws configure
```

Inputs:

```text
AWS Access Key ID: your key
AWS Secret Access Key: your secret
Default region name: eu-central-1
Default output format: json
```

Verify:

```powershell
aws sts get-caller-identity
```

Expected:

```json
{
  "Account": "...",
  "Arn": "arn:aws:iam::ACCOUNT_ID:user/rag-chatbot"
}
```

Never share or commit access keys.

---

## 11. AWS ECR

ECR means Elastic Container Registry.

Purpose:

Store Docker images in AWS.

Create repository:

```powershell
aws ecr create-repository --repository-name rag-chatbot-backend --region eu-central-1
```

Repository ARN:

```text
arn:aws:ecr:eu-central-1:281639842123:repository/rag-chatbot-backend
```

Image URI:

```text
281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-backend:latest
```

Login Docker to ECR:

```powershell
aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin 281639842123.dkr.ecr.eu-central-1.amazonaws.com
```

Tag local image:

```powershell
docker tag codemars-rag-backend:latest 281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-backend:latest
```

Push image:

```powershell
docker push 281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-backend:latest
```

Common error:

```text
tag does not exist
```

Cause:

The local image was not tagged with the ECR URI.

Fix:

Run `docker tag ...` before `docker push`.

---

## 12. AWS EC2

Purpose:

Run a remote Ubuntu server in AWS.

Instance created:

```text
codemars-rag-backend-server
```

Recommended learning settings:

```text
AMI: Ubuntu Server 24.04 LTS
Instance type: t3.micro or free-tier eligible type
Storage: 8 GB gp3
Region: eu-central-1
Security group:
  SSH 22 from My IP
  TCP 8000 from My IP
```

Key pair:

```text
rag-chatbot-key.pem
```

SSH command:

```powershell
ssh -i "F:\ML Project\Resource and documents\rag-chatbot-key.pem" ubuntu@13.49.241.90
```

If key permissions are too open on Windows:

```powershell
whoami
icacls "F:\ML Project\Resource and documents\rag-chatbot-key.pem" /inheritance:r
icacls "F:\ML Project\Resource and documents\rag-chatbot-key.pem" /grant "tamim\mdtam:R"
icacls "F:\ML Project\Resource and documents\rag-chatbot-key.pem"
```

Expected SSH prompt:

```text
ubuntu@ip-...:~$
```

---

## 13. Install Docker On EC2

Run inside EC2:

```bash
sudo apt update
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu
newgrp docker
```

Test:

```bash
docker --version
docker ps
```

Why:

EC2 is just a Linux server. Docker must be installed before it can run
containers.

---

## 14. EC2 IAM Role For ECR Pull

Best practice:

Do not put AWS access keys on EC2.

Instead, attach an IAM role to EC2.

Role created:

```text
codemars-ec2-ecr-readonly-role
```

Trusted entity:

```text
AWS service -> EC2
```

Policy:

```text
AmazonEC2ContainerRegistryReadOnly
```

Attach to instance:

```text
EC2 -> Instances -> select instance
Actions -> Security -> Modify IAM role
Choose codemars-ec2-ecr-readonly-role
Update IAM role
```

Why:

EC2 only needs to pull images from ECR, not push or create repositories.

---

## 15. Current Project State

Completed:

- backend Docker image built locally
- frontend Docker image built locally
- Docker Compose works locally
- nginx proxies `/api/*` to backend
- GitHub Actions CI works
- Docker build checks run in CI
- AWS CLI configured for new account
- ECR repo created
- backend image pushed to ECR
- EC2 Ubuntu instance running
- SSH access works
- Docker installed on EC2
- EC2 IAM role attached for ECR read-only access

Current ECR image:

```text
281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-backend:latest
```

Next step:

```text
SSH into EC2
login/pull image from ECR using EC2 IAM role
run backend container
test public EC2 URL on port 8000
```

---

## 16. Useful Cleanup Commands

Stop local Compose:

```powershell
docker compose down
```

Delete local Compose volumes:

```powershell
docker compose down -v
```

Stop EC2 instance:

```text
EC2 Console -> Instances -> select instance -> Instance state -> Stop
```

Terminate EC2 instance:

```text
EC2 Console -> Instances -> select instance -> Instance state -> Terminate
```

Delete ECR repository:

```powershell
aws ecr delete-repository --repository-name rag-chatbot-backend --region eu-central-1 --force
```

Warning:

Deleting ECR repository removes stored images.

---

## 17. Cost Safety Notes

Always set budget alerts.

AWS services that can cost money:

- EC2 running instance
- EBS storage
- public IPv4 address
- ECR image storage
- CloudWatch logs
- data transfer

Recommended:

- stop/terminate EC2 when not learning
- delete unused ECR images
- keep instance size free-tier eligible
- avoid load balancers until you understand cost

