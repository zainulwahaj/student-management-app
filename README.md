# DevOps Assignment 3 — Selenium Tests in a Jenkins Pipeline

A simple **Student Management System** (Flask + MySQL) tested with **24 Selenium test cases** running against headless Chromium inside Docker, orchestrated by a **Jenkins pipeline** on AWS EC2.

---

## 1. What's in this repo

```
devops-assignment/
├── app/                    # Flask web application
│   ├── app.py              #   - Auth (register/login/logout) + Student CRUD
│   ├── templates/          #   - Bootstrap-styled Jinja templates
│   ├── requirements.txt
│   ├── entrypoint.sh       #   - Waits for MySQL, creates schema, starts gunicorn
│   └── Dockerfile
├── tests/                  # Selenium test suite
│   ├── test_selenium.py    #   - 24 test cases (headless Chromium)
│   ├── conftest.py         #   - Shared fixtures + driver setup
│   ├── requirements.txt
│   └── Dockerfile          #   - Python + Chromium + chromedriver
├── docker-compose.yml      # Three services: db, app, tests
├── Jenkinsfile             # Pipeline: checkout → build → deploy → test → email
├── scripts/
│   └── ec2-bootstrap.sh    # One-shot EC2 setup (Docker + Jenkins + Java)
└── README.md
```

The web app uses **MySQL 8** as its database server (running as a separate container) — satisfying the "uses some Database Server" requirement.

---

## 2. Local quick test (optional)

If you have Docker locally:

```bash
docker compose build
docker compose up -d db app
# wait ~15 seconds for the DB+app to come up, then:
docker compose run --rm tests
```

The web app is reachable at <http://localhost:5000>.
HTML test report is written to `tests/reports/report.html`.

---

## 3. EC2 setup (one time)

### 3.1 Launch an instance
- AMI: **Ubuntu 22.04 LTS** (or 24.04)
- Type: **t3.medium** or larger (Selenium + Docker + Jenkins is RAM-hungry; `t2.micro` will OOM)
- Storage: **20 GB** minimum
- Security Group inbound rules:
  | Port | Source | Purpose |
  |-----:|---|---|
  | 22   | your IP | SSH |
  | 8080 | your IP | Jenkins UI |
  | 5000 | 0.0.0.0/0 (or your IP) | Deployed Flask app |

### 3.2 Run the bootstrap script
SSH in and run:
```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/<you>/<repo>.git
cd <repo>
sudo bash scripts/ec2-bootstrap.sh
```

This installs Docker, the docker-compose plugin, Java 17, and Jenkins, then adds the `jenkins` user to the `docker` group.

### 3.3 Initial Jenkins login
```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```
Open `http://<ec2-public-ip>:8080`, paste the password, and choose **Install suggested plugins**. Create your admin user.

### 3.4 Install required plugins
**Manage Jenkins → Plugins → Available**, install:
- **Pipeline** *(usually already installed)*
- **Git**
- **Docker Pipeline**
- **Email Extension Plugin** (`emailext`)
- **HTML Publisher**
- **AnsiColor**
- **Timestamper**
- **GitHub Integration**

Restart Jenkins when prompted.

---

## 4. Configure Jenkins

### 4.1 Email (SMTP) — required for the test-result email
**Manage Jenkins → System → Extended E-mail Notification**:

For Gmail (recommended, easy):
- SMTP Server: `smtp.gmail.com`
- SMTP Port: `465`
- Use SSL: ☑
- Credentials: add **Username with password**
  - Username = your Gmail address
  - Password = a [Gmail App Password](https://myaccount.google.com/apppasswords) (NOT your normal password — you must enable 2FA, then create an App Password)
- Default user e-mail suffix: `@gmail.com`
- Default Content Type: `HTML (text/html)`

Also fill in **Jenkins Location → System Admin e-mail address** with the same Gmail.

Click **Test configuration by sending test e-mail** to a recipient before continuing.

### 4.2 Create the pipeline job
**New Item → Pipeline → name it `sms-pipeline`**:

- ☑ **GitHub project** → URL of your repo
- **Build Triggers** → ☑ **GitHub hook trigger for GITScm polling**
- **Pipeline**:
  - Definition: **Pipeline script from SCM**
  - SCM: **Git**
  - Repository URL: `https://github.com/<you>/<repo>.git`
  - Credentials: add a GitHub token if the repo is private
  - Branch: `*/main` (or whatever you use)
  - Script Path: `Jenkinsfile`
- **Save**.

### 4.3 GitHub webhook
On your repo: **Settings → Webhooks → Add webhook**:
- Payload URL: `http://<ec2-public-ip>:8080/github-webhook/`
- Content type: `application/json`
- Events: **Just the push event**
- Active: ☑

### 4.4 Add the instructor as collaborator
On your repo: **Settings → Collaborators → Add `qasimalik@gmail.com`**.
Their first push (e.g. an empty README edit) will fire the webhook → Jenkins → tests → email the result to `qasimalik@gmail.com`.

---

## 5. How the pipeline works

| Stage | Action |
|---|---|
| **Checkout** | `git clone` + capture committer email/name/SHA from `git log -1` |
| **Build images** | `docker compose build --pull` (app image + tests image) |
| **Deploy app + DB** | `docker compose up -d db app` and wait until app's health check returns healthy |
| **Run Selenium tests** | `docker compose run --rm tests` — 24 headless-Chromium tests, output as JUnit XML + HTML report |
| **post / always** | Archive the HTML report, publish JUnit results, email the report to the committer via `emailext` |
| **post / failure** | Tear the containers down |
| **post / success** | **Leave the deployment running on port 5000** — matches assignment requirement that the deployment comes UP when the collaborator pushes |

Email subject example:
`✅ [Jenkins] sms-pipeline #4 — SUCCESS`

The HTML test report is attached to the email.

---

## 6. Two-repo layout (what the assignment asks for)

The assignment wants **the application code and the test code in different GitHub repos**. To do that, split this folder:

**Repo A — application** (`student-management-app`):
- `app/`
- `docker-compose.yml`
- `Jenkinsfile`
- `scripts/`
- `.gitignore`, `.dockerignore`, `README.md`
- Add a small step in the Jenkinsfile's *Checkout* stage to also clone the test repo into `tests/`:
  ```groovy
  stage('Checkout') {
      steps {
          checkout scm
          dir('tests') {
              git branch: 'main',
                  url: 'https://github.com/<you>/student-management-tests.git'
          }
          // ... committer info ...
      }
  }
  ```

**Repo B — tests** (`student-management-tests`):
- everything currently in `tests/`

The webhook lives on **Repo A** (the app). When the instructor pushes to the app repo, Jenkins clones both repos, runs the tests, and emails him.

If you want to keep it as a single repo for simplicity (still graded per the assignment criteria), you can — the Jenkinsfile already works that way without modification.

---

## 7. Submission checklist

Per the Google Form in the assignment PDF:

- [ ] **Deployment URL**: `http://<ec2-public-ip>:5000`
- [ ] **Application repo URL**: GitHub link
- [ ] **Test repo URL**: GitHub link (if split) — otherwise reuse the same one
- [ ] **Sender email** configured in Jenkins email-ext (your Gmail)
- [ ] Add `qasimalik@gmail.com` as collaborator
- [ ] Stop containers before submitting: `docker compose down` (the assignment says "must be down initially")
- [ ] Report PDF with screenshots of:
  - Web app pages (home, register, login, dashboard, students)
  - At least one passing Selenium test (terminal/`report.html`)
  - Jenkinsfile contents
  - Jenkins pipeline showing all stages green
  - The test-result email received in your inbox

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `permission denied: /var/run/docker.sock` in Jenkins | `sudo usermod -aG docker jenkins && sudo systemctl restart jenkins` |
| `chromedriver: cannot connect to chrome` | Make sure tests run in the `tests` container (the Dockerfile installs matching `chromium` + `chromium-driver`); don't run pytest from the host |
| Email not arriving | Use a Gmail **App Password**, not your real password. 2FA must be on |
| Webhook not firing | EC2 SG must allow inbound 8080. Test with `curl -X POST http://<ec2>:8080/github-webhook/` — should return 200 |
| Tests fail with `connection refused` to `http://app:5000` | The app container isn't healthy — `docker compose logs app` |
| MySQL container restart loop | Out of disk or `db_data` volume corrupt: `docker compose down -v` and rebuild |

---

## 9. Local development tip

To run the app without Docker (for development):
```bash
cd app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# point at any local MySQL, or run one in Docker:
docker run -d --name dev-mysql -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=students_db \
  mysql:8.0

export DB_HOST=localhost
python app.py  # http://localhost:5000
```
