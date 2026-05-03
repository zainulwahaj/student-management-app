pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        ansiColor('xterm')
    }

    environment {
        COMPOSE_PROJECT_NAME = 'sms'
        // ── Update this to your test repo URL before running ──────────────
        TEST_REPO_URL = 'https://github.com/zainulwahaj/student-management-tests.git'
        TEST_REPO_BRANCH = 'main'
    }

    stages {

        stage('Checkout') {
            steps {
                // 1. Checkout the application repo (triggered by the webhook)
                checkout scm

                // 2. Capture committer details for the result email
                script {
                    env.COMMITTER_EMAIL = sh(returnStdout: true,
                        script: "git log -1 --pretty=format:'%ae'").trim()
                    env.COMMITTER_NAME  = sh(returnStdout: true,
                        script: "git log -1 --pretty=format:'%an'").trim()
                    env.COMMIT_MSG      = sh(returnStdout: true,
                        script: "git log -1 --pretty=format:'%s'").trim()
                    env.COMMIT_SHA      = sh(returnStdout: true,
                        script: "git log -1 --pretty=format:'%h'").trim()
                    echo "Triggered by ${env.COMMITTER_NAME} <${env.COMMITTER_EMAIL}>"
                }

                // 3. Clone the separate test repo into ./tests/
                dir('tests') {
                    git branch: env.TEST_REPO_BRANCH, url: env.TEST_REPO_URL
                }
            }
        }

        stage('Build images') {
            steps {
                // Builds both the app image (./app) and the test image (./tests)
                sh 'docker compose build --pull app tests'
            }
        }

        stage('Deploy app + DB') {
            steps {
                sh '''
                    docker rm -f sms_db sms_app sms_tests 2>/dev/null || true
                    docker compose up -d db app
                '''
                sh '''
                    echo "Waiting for sms_app Docker health=healthy (required for compose run tests)..."
                    for i in $(seq 1 100); do
                        H=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' sms_app 2>/dev/null || echo "unknown")
                        if curl -fsS --max-time 2 "http://127.0.0.1:5000/" >/dev/null 2>&1; then HTTP=ok; else HTTP=no; fi
                        if [ "$H" = "healthy" ]; then
                            echo "  attempt $i: healthy (host_http=$HTTP)"
                            exit 0
                        fi
                        if [ "$H" = "unhealthy" ]; then
                            echo "  attempt $i: UNHEALTHY (host_http=$HTTP)"
                            docker inspect --format='{{json .State.Health}}' sms_app 2>/dev/null || true
                            docker compose logs --tail=200 app
                            exit 1
                        fi
                        echo "  attempt $i: health=$H host_http=$HTTP"
                        sleep 2
                    done
                    echo "Timed out waiting for healthy."
                    docker inspect --format='{{json .State.Health}}' sms_app 2>/dev/null || true
                    docker compose logs --tail=200 app
                    exit 1
                '''
            }
        }

        stage('Run Selenium tests') {
            steps {
                sh 'mkdir -p tests/reports && chmod 777 tests/reports'
                sh 'docker compose run --rm tests'
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'tests/reports/**', allowEmptyArchive: true
            junit allowEmptyResults: true, testResults: 'tests/reports/junit.xml'

            script {
                def status  = currentBuild.currentResult
                def color   = (status == 'SUCCESS') ? '#1a7f37' : '#cf222e'
                def emoji   = (status == 'SUCCESS') ? '✅' : '❌'
                def subject = "${emoji} [Jenkins] ${env.JOB_NAME} #${env.BUILD_NUMBER} — ${status}"
                def body    = """
                    <div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;
                                max-width:600px;padding:20px;border:1px solid #ddd;border-radius:8px">
                      <h2 style="color:${color};margin-top:0">${emoji} Build ${status}</h2>
                      <table cellpadding="6" style="border-collapse:collapse;width:100%">
                        <tr><td><b>Job</b></td><td>${env.JOB_NAME}</td></tr>
                        <tr><td><b>Build</b></td><td>#${env.BUILD_NUMBER}</td></tr>
                        <tr><td><b>Commit</b></td><td><code>${env.COMMIT_SHA}</code> — ${env.COMMIT_MSG}</td></tr>
                        <tr><td><b>Pushed by</b></td><td>${env.COMMITTER_NAME} &lt;${env.COMMITTER_EMAIL}&gt;</td></tr>
                        <tr><td><b>Duration</b></td><td>${currentBuild.durationString}</td></tr>
                      </table>
                      <p style="margin-top:16px">
                        <a href="${env.BUILD_URL}" style="background:${color};color:#fff;padding:8px 14px;
                           border-radius:6px;text-decoration:none">Open build in Jenkins →</a>
                      </p>
                      <p>Full HTML test report is attached to this email.</p>
                    </div>
                """.stripIndent()

                emailext(
                    to:                 env.COMMITTER_EMAIL,
                    subject:            subject,
                    body:               body,
                    mimeType:           'text/html',
                    attachLog:          true,
                    attachmentsPattern: 'tests/reports/report.html'
                )
            }
        }

        failure {
            echo 'Build failed — leaving app and DB containers running for inspection.'
        }

        success {
            echo 'Tests passed — deployment is running on port 5000.'
        }
    }
}
