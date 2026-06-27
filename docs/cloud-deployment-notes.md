# Cloud Deployment Notes

Project: Secure Enterprise RAG Chatbot / Codemars Intranet

Goal:

```text
Learn and build a real deployment path:
Docker -> Docker Compose -> GitHub Actions CI -> AWS ECR -> AWS EC2 -> CI/CD deployment
```

This document is written as a learning guide. Each step explains:

- what the step does
- why it is needed
- which command to run
- what result to expect
- common problems and fixes

---

## 1. Final Architecture

Current deployed architecture:

```text
User browser
  -> EC2 public IP on port 80
  -> frontend nginx container
  -> Vue static app
  -> /api/* requests
  -> backend FastAPI container on port 8000
  -> RAG chatbot service
```

Current cloud resources:

```text
AWS account ID: 281639842123
ECR region: eu-central-1
EC2 user: ubuntu
Backend ECR image:
  281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-backend:latest
Frontend ECR image:
  281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-frontend:latest
```

Current public checks:

```text
Backend docs:
http://13.49.241.90:8000/docs

Frontend app:
http://13.49.241.90
```

Important:

If EC2 is stopped and started again, the public IP can change unless you attach
an Elastic IP. Update all commands and GitHub secrets with the new public IP.

---

## 2. Why Docker Is Used

Docker packages an application with its runtime and dependencies.

For this project:

```text
Backend image:
  Python + FastAPI + backend code + dependencies

Frontend image:
  Vue build files + nginx web server
```

Key terms:

```text
Dockerfile:
  Recipe for building an image.

Image:
  Packaged application template.

Container:
  Running instance of an image.

Registry:
  Storage for Docker images. AWS ECR is a registry.

Docker network:
  Allows containers to communicate by name.

Docker volume:
  Persistent storage managed by Docker.
```

Why Docker matters:

```text
Same app can run locally, in GitHub Actions, and on EC2.
Deployment becomes repeatable.
EC2 does not need your source code structure, only Docker images.
```

---

## 3. Backend Dockerfile

File:

```text
backend/Dockerfile
```

Content:

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

```text
FROM python:3.12-slim
  Starts from a lightweight official Python image.

ENV PYTHONDONTWRITEBYTECODE=1
  Prevents Python from creating .pyc cache files.

ENV PYTHONUNBUFFERED=1
  Makes logs print immediately.

ENV PYTHONPATH=/app
  Allows imports like backend.main.

WORKDIR /app
  Sets /app as the working directory inside the container.

apt-get install build-essential
  Installs Linux build tools needed by some Python packages.

COPY backend/requirements.txt first
  Helps Docker cache dependency installation.

pip install --no-cache-dir
  Installs Python dependencies without keeping pip cache.

COPY backend
  Copies backend source code and data.

EXPOSE 8000
  Documents that the app uses port 8000.

CMD uvicorn --host 0.0.0.0
  Starts FastAPI and allows connections from outside the container.
```

Build backend image locally:

```powershell
docker build --file backend/Dockerfile --tag codemars-rag-backend .
```

Why:

```text
Creates a local Docker image named codemars-rag-backend.
```

Run backend locally:

```powershell
docker run --rm -p 8000:8000 codemars-rag-backend
```

Why:

```text
Maps your computer port 8000 to the container port 8000.
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

## 4. Docker Ignore

File:

```text
.dockerignore
```

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

```text
Docker sends files to the Docker engine during build.
.dockerignore keeps builds smaller, faster, and safer.
It also prevents secrets and virtual environments from entering images.
```

---

## 5. Frontend Dockerfile

File:

```text
frontend/Dockerfile
```

Content:

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

```text
This is a multi-stage build.

Stage 1: Node builds the Vue app.
Stage 2: nginx serves the built static files.

The final image does not contain node_modules or the Node build tools.
```

Build frontend image locally:

```powershell
docker build --file frontend/Dockerfile --tag rag-chatbot-frontend .
```

Run frontend locally:

```powershell
docker run --rm -p 5173:80 rag-chatbot-frontend
```

Test:

```text
http://localhost:5173
```

---

## 6. nginx Reverse Proxy

File:

```text
frontend/nginx.conf
```

Content:

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

```text
1. Serves the Vue app.
2. Forwards frontend API calls to backend.
3. Supports Vue single-page routing.
```

Important proxy behavior:

```text
Browser calls:
  /api/health

nginx forwards to:
  http://backend:8000/health
```

Important Docker lesson:

```text
backend is not an internet domain.
backend is the Docker container name or Docker network alias.
The frontend container can resolve backend only if both containers are in the same Docker network.
```

---

## 7. Docker Compose For Local Multi-Container Run

File:

```text
docker-compose.yml
```

Purpose:

```text
Run backend and frontend together locally with one command.
```

Useful command:

```powershell
docker compose up --build
```

Why:

```text
Builds both images and starts both containers.
```

Test local frontend:

```text
http://localhost:5173
```

Test local API through frontend nginx:

```text
http://localhost:5173/api/health
```

Expected:

```json
{"status":"ok"}
```

Stop containers:

```powershell
docker compose down
```

Stop containers and delete volumes:

```powershell
docker compose down -v
```

Why volumes matter:

```text
backend_logs stores monitoring logs.
chroma_data stores Chroma vector database data.
```

---

## 8. Environment Variables

Local files:

```text
.env.example
.env
```

Example:

```env
LLM_PROVIDER=fake
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b
EMBEDDING_PROVIDER=hash
```

Meaning:

```text
LLM_PROVIDER
  Controls which LLM backend to use. Example: fake or groq.

GROQ_API_KEY
  Secret API key for Groq.

GROQ_MODEL
  Model name used by Groq.

EMBEDDING_PROVIDER
  hash means use local hash embeddings, not paid API embeddings.
```

Why:

```text
Secrets should not be hardcoded.
Different environments need different values.
Local Docker, EC2, and GitHub Actions can all inject env variables.
```

Check Compose config:

```powershell
docker compose config
```

---

## 9. GitHub Actions CI

File:

```text
.github/workflows/ci.yml
```

CI means Continuous Integration.

Purpose:

```text
Automatically check code whenever you push or open a pull request.
```

Current CI checks:

```text
backend-tests:
  Install Python dependencies.
  Run backend unit tests.
  Run RAG evaluation.

frontend-build:
  Install Node dependencies.
  Build Vue app.

docker-build:
  Build backend Docker image.
  Build frontend Docker image.
```

Important lesson:

```text
GitHub Actions starts from the repository root.
So the backend dependency path must be backend/requirements.txt,
not requirements.txt.
```

Run tests locally before pushing:

```powershell
python -m unittest discover backend/tests -v
```

Run frontend build locally:

```powershell
cd frontend
npm run build
cd ..
```

Check git status:

```powershell
git status --short
```

---

## 10. AWS CLI Setup

AWS CLI lets your terminal talk to AWS.

Install check:

```powershell
aws --version
```

Configure:

```powershell
aws configure
```

Inputs:

```text
AWS Access Key ID: your access key
AWS Secret Access Key: your secret key
Default region name: eu-central-1
Default output format: json
```

Verify identity:

```powershell
aws sts get-caller-identity
```

Expected:

```json
{
  "Account": "281639842123",
  "Arn": "arn:aws:iam::281639842123:user/rag-chatbot"
}
```

Why:

```text
This confirms your terminal is authenticated to the correct AWS account.
```

---

## 11. AWS IAM User

Created IAM user:

```text
rag-chatbot
```

Why:

```text
The local AWS CLI needs permission to create ECR repos and push Docker images.
```

Learning policies used:

```text
AmazonEC2FullAccess
AmazonEC2ContainerRegistryPowerUser
```

Important:

```text
Never commit AWS access keys.
Never paste AWS secret keys into normal code files.
Use GitHub Secrets for CI/CD.
```

---

## 12. AWS ECR

ECR means Elastic Container Registry.

Purpose:

```text
Store Docker images in AWS.
GitHub Actions pushes images to ECR.
EC2 pulls images from ECR.
```

Create backend repository:

```powershell
aws ecr create-repository --repository-name rag-chatbot-backend --region eu-central-1
```

Create frontend repository:

```powershell
aws ecr create-repository --repository-name rag-chatbot-frontend --region eu-central-1
```

Login Docker to ECR:

```powershell
aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin 281639842123.dkr.ecr.eu-central-1.amazonaws.com
```

Why:

```text
Docker must authenticate before it can push images to a private ECR registry.
```

Build backend:

```powershell
docker build --file backend/Dockerfile --tag codemars-rag-backend .
```

Tag backend for ECR:

```powershell
docker tag codemars-rag-backend:latest 281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-backend:latest
```

Push backend:

```powershell
docker push 281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-backend:latest
```

Build frontend:

```powershell
docker build --file frontend/Dockerfile --tag rag-chatbot-frontend .
```

Tag frontend for ECR:

```powershell
docker tag rag-chatbot-frontend:latest 281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-frontend:latest
```

Push frontend:

```powershell
docker push 281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-frontend:latest
```

Common error:

```text
tag does not exist
```

Cause:

```text
The local image name was misspelled or not tagged with the ECR URI.
```

Fix:

```powershell
docker images
docker tag CORRECT_LOCAL_IMAGE:latest ECR_IMAGE_URI:latest
```

---

## 13. AWS EC2

EC2 means Elastic Compute Cloud.

Purpose:

```text
Run a Linux server in AWS where Docker containers can run.
```

Instance setup:

```text
AMI: Ubuntu Server 24.04 LTS
Instance type: free-tier eligible type
Key pair: rag-chatbot-key.pem
User: ubuntu
```

SSH command:

```powershell
ssh -i "F:\ML Project\Resource and documents\rag-chatbot-key.pem" ubuntu@13.49.241.90
```

Why:

```text
SSH gives terminal access to the remote Ubuntu server.
```

If key permissions are too open on Windows:

```powershell
whoami
icacls "F:\ML Project\Resource and documents\rag-chatbot-key.pem" /inheritance:r
icacls "F:\ML Project\Resource and documents\rag-chatbot-key.pem" /grant "tamim\mdtam:R"
icacls "F:\ML Project\Resource and documents\rag-chatbot-key.pem"
```

Common SSH timeout:

```text
ssh: connect to host ... port 22: Connection timed out
```

Possible causes:

```text
Wrong public IP.
Instance stopped.
Wrong AWS region selected.
Security Group does not allow SSH.
```

---

## 14. EC2 Security Group

Security Group is the firewall for EC2.

Rules used while learning:

```text
SSH:
  Port: 22
  Source: My IP or temporary 0.0.0.0/0 for GitHub Actions SSH

HTTP:
  Port: 80
  Source: 0.0.0.0/0

Backend direct access:
  Port: 8000
  Source: 0.0.0.0/0 for testing
```

Why:

```text
Port 22 is needed for SSH.
Port 80 is needed for browser access to frontend.
Port 8000 was used to test FastAPI directly.
```

Production improvement:

```text
After frontend nginx works, port 8000 can be closed publicly.
The browser should use port 80, and nginx should call backend internally.
```

GitHub Actions SSH issue:

```text
SSH 22 from My IP works only from your computer.
GitHub Actions runs from GitHub servers, so it is blocked.
For learning, SSH 22 was temporarily opened to 0.0.0.0/0.
```

---

## 15. Install Docker On EC2

Run inside EC2:

```bash
sudo apt update
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu
newgrp docker
```

Explanation:

```text
apt update:
  Refreshes Ubuntu package list.

apt install docker.io:
  Installs Docker.

systemctl start docker:
  Starts Docker now.

systemctl enable docker:
  Starts Docker automatically after reboot.

usermod -aG docker ubuntu:
  Lets ubuntu user run docker without sudo.

newgrp docker:
  Applies the group change in the current SSH session.
```

Test:

```bash
docker --version
docker ps
```

Expected:

```text
docker ps should run without permission error.
```

---

## 16. EC2 IAM Role For ECR Pull

Best practice:

```text
Do not store AWS access keys on EC2.
Attach an IAM role to EC2 instead.
```

Role created:

```text
codemars-ec2-ecr-readonly-role
```

Policy:

```text
AmazonEC2ContainerRegistryReadOnly
```

Attach role:

```text
EC2 Console
  -> Instances
  -> select instance
  -> Actions
  -> Security
  -> Modify IAM role
  -> choose codemars-ec2-ecr-readonly-role
```

Why:

```text
EC2 only needs to pull images from ECR.
It does not need permission to create repositories or push images.
```

---

## 17. Pull And Run Backend On EC2

Login to ECR from EC2:

```bash
aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin 281639842123.dkr.ecr.eu-central-1.amazonaws.com
```

Pull backend:

```bash
docker pull 281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-backend:latest
```

Run backend:

```bash
docker run -d \
  --name rag-chatbot-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  -e LLM_PROVIDER=groq \
  -e GROQ_API_KEY="your_groq_key_here" \
  -e GROQ_MODEL=openai/gpt-oss-20b \
  -e EMBEDDING_PROVIDER=hash \
  281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-backend:latest
```

Explanation:

```text
-d:
  Run container in background.

--name rag-chatbot-backend:
  Gives container a name.

--restart unless-stopped:
  Restarts container automatically after EC2 reboot.

-p 8000:8000:
  Maps EC2 port 8000 to container port 8000.

-e:
  Passes environment variables into the container.
```

Check running containers:

```bash
docker ps
```

Test inside EC2:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

Test from browser:

```text
http://13.49.241.90:8000/docs
```

---

## 18. Pull And Run Frontend On EC2

Pull frontend:

```bash
docker pull 281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-frontend:latest
```

Create Docker network:

```bash
docker network create rag-network
```

Why:

```text
The frontend nginx container needs to call backend by the name backend.
Docker networks allow containers to find each other by name or alias.
```

Connect existing backend with alias:

```bash
docker network connect --alias backend rag-network rag-chatbot-backend
```

Why:

```text
The existing backend container is named rag-chatbot-backend.
nginx expects backend.
The alias makes rag-chatbot-backend reachable as backend.
```

Run frontend:

```bash
docker run -d \
  --name frontend \
  --restart unless-stopped \
  --network rag-network \
  -p 80:80 \
  281639842123.dkr.ecr.eu-central-1.amazonaws.com/rag-chatbot-frontend:latest
```

Test from EC2:

```bash
curl http://localhost
curl http://localhost/api/health
```

Expected:

```text
curl http://localhost should return HTML.
curl http://localhost/api/health should return {"status":"ok"}.
```

Test from browser:

```text
http://13.49.241.90
```

---

## 19. Useful Docker Commands On EC2

Show running containers:

```bash
docker ps
```

Show all containers:

```bash
docker ps -a
```

Show images:

```bash
docker images
```

Show logs:

```bash
docker logs backend
docker logs frontend
docker logs rag-chatbot-backend
```

Stop container:

```bash
docker stop frontend
```

Remove container:

```bash
docker rm frontend
```

Remove unused Docker data:

```bash
docker system prune -af --volumes
```

Check disk:

```bash
df -h
docker system df
```

---

## 20. Disk Space Problem We Hit

Error:

```text
no space left on device
```

Cause:

```text
The backend image originally pulled heavy ML dependencies.
The log showed NVIDIA CUDA files like libcublasLt.so.
This happened because sentence-transformers/PyTorch dependencies were too large.
```

Fix:

```text
Use EMBEDDING_PROVIDER=hash for this deployment.
Remove unused heavy embedding dependencies from backend/requirements.txt.
Rebuild and push a smaller backend image.
```

Why:

```text
Free-tier EC2 storage is small.
Large ML images can fill the disk before extraction finishes.
```

---

## 21. GitHub Secrets For CI/CD

GitHub Secrets location:

```text
GitHub repo
  -> Settings
  -> Secrets and variables
  -> Actions
  -> New repository secret
```

Secrets added:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
AWS_ACCOUNT_ID
EC2_HOST
EC2_USER
EC2_SSH_KEY
GROQ_API_KEY
```

Values:

```text
AWS_REGION=eu-central-1
AWS_ACCOUNT_ID=281639842123
EC2_USER=ubuntu
EC2_HOST=current EC2 public IPv4 address
EC2_SSH_KEY=full private key content from rag-chatbot-key.pem
GROQ_API_KEY=your Groq API key
```

Why:

```text
GitHub Actions needs AWS credentials to push images to ECR.
GitHub Actions needs SSH key and EC2 host to deploy to EC2.
Secrets keep these values out of source code.
```

Important:

```text
If EC2 public IP changes, update EC2_HOST.
If the private key is copied incorrectly, SSH deployment fails.
```

---

## 22. GitHub Actions CD Job

CD means Continuous Deployment.

Purpose:

```text
After tests pass on master, automatically build images, push to ECR,
SSH into EC2, pull latest images, and restart containers.
```

Current deploy flow:

```text
git push origin master
  -> GitHub Actions starts
  -> backend tests pass
  -> frontend build passes
  -> Docker builds pass
  -> deploy job builds and pushes ECR images
  -> deploy job SSHs into EC2
  -> EC2 pulls latest images
  -> containers restart
  -> health checks run
```

Command to commit workflow changes:

```powershell
git status --short
git add .github/workflows/ci.yml docs/cloud-deployment-notes.md
git commit -m "Add EC2 deployment workflow"
git push origin master
```

Watch deployment:

```text
GitHub repo
  -> Actions
  -> CI
  -> latest run
```

Common GitHub Actions SSH error:

```text
ssh: connect to host ... port 22: Connection timed out
```

Cause:

```text
EC2 Security Group allows SSH only from your IP.
GitHub Actions runs from GitHub servers, so it is blocked.
```

Learning fix:

```text
Temporarily allow SSH 22 from 0.0.0.0/0.
Then re-run failed jobs.
```

Better future fixes:

```text
Use AWS Systems Manager instead of SSH.
Use a self-hosted GitHub runner on EC2.
Restrict SSH more carefully.
```

---

## 23. Why ECR Is Used Instead Of Direct EC2 Build

You can deploy directly to EC2 without ECR.

Direct EC2 deployment:

```text
GitHub Actions
  -> SSH into EC2
  -> git pull
  -> docker build on EC2
  -> restart containers
```

ECR deployment:

```text
GitHub Actions
  -> build Docker images
  -> push images to ECR
  -> SSH into EC2
  -> docker pull images
  -> restart containers
```

Why ECR is better for this project:

```text
EC2 does less work.
Small free-tier EC2 avoids heavy image builds.
Images are stored as deployable artifacts.
Rollback is easier.
This is closer to real production practice.
ECR knowledge transfers to ECS, EKS, and other cloud deployments.
```

---

## 24. Cost Safety

AWS services that can cost money:

```text
EC2 running instance
EBS storage
Public IPv4 address
ECR image storage
CloudWatch logs
Data transfer
Elastic IP if unused
```

Recommended habits:

```text
Set AWS budget alerts.
Stop or terminate EC2 when not learning.
Delete unused ECR images.
Avoid load balancers until you understand pricing.
Keep storage and instance size small while learning.
```

Stop EC2:

```text
AWS Console
  -> EC2
  -> Instances
  -> select instance
  -> Instance state
  -> Stop instance
```

Terminate EC2:

```text
AWS Console
  -> EC2
  -> Instances
  -> select instance
  -> Instance state
  -> Terminate instance
```

Delete ECR repositories:

```powershell
aws ecr delete-repository --repository-name rag-chatbot-backend --region eu-central-1 --force
aws ecr delete-repository --repository-name rag-chatbot-frontend --region eu-central-1 --force
```

---

## 25. Learning Summary

You have learned and built:

```text
Dockerfile for Python backend
Dockerfile for Vue frontend
nginx static serving and reverse proxy
Docker Compose local multi-container setup
environment variables and secrets
GitHub Actions CI
AWS IAM user
AWS CLI
AWS ECR repositories
Docker image tagging and pushing
AWS EC2 Ubuntu server
SSH access with key pair
Windows SSH key permission fixes
EC2 Security Groups
Docker installation on EC2
EC2 IAM role for ECR pull
container networking
public backend deployment
public frontend deployment
GitHub Actions CI/CD deployment design
```

Main idea to remember:

```text
Docker packages the app.
ECR stores the package.
EC2 runs the package.
GitHub Actions automates the process.
nginx connects the browser frontend to the backend API.
```
