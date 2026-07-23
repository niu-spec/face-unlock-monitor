// home-camera-monitor — optional Jenkins Pipeline (CD on your own server)
// See deploy/README.md and deploy/install_jenkins.sh

pipeline {
    agent any

    options {
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    triggers {
        // GitHub webhook is preferred; pollSCM is a fallback when webhook is unavailable.
        pollSCM('H/5 * * * *')
    }

    environment {
        CI = 'true'
        DJANGO_SECRET_KEY = 'jenkins-ci-test-secret-key'
        DJANGO_DEBUG = 'True'
        DEPLOY_PATH = '/service/home-camera-monitor'
        DEPLOY_MEDIAMTX = '0'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Backend Test') {
            steps {
                sh 'bash scripts/ci-backend-test.sh'
            }
        }

        stage('Frontend Build') {
            steps {
                sh 'bash scripts/ci-frontend-build.sh'
            }
        }

        stage('Deploy Production') {
            when {
                anyOf {
                    branch 'dev'
                    branch 'main'
                }
            }
            steps {
                input message: 'Deploy to production server?', ok: 'Deploy'
                sh '''
                    set -euo pipefail
                    BR="${BRANCH_NAME:-dev}"
                    APP="${DEPLOY_PATH}"
                    cd "$APP"
                    git fetch origin "$BR" 2>/dev/null || true
                    git checkout "$BR"
                    TARGET="${GIT_COMMIT:-origin/$BR}"
                    if ! git merge --ff-only "$TARGET" 2>/dev/null; then
                      echo "[deploy] ff-only failed; update tracked files only (untracked preserved)"
                      git checkout "$TARGET" -- .
                      git update-ref "refs/heads/$BR" "$TARGET"
                    fi
                    DEPLOY_USE_SUDO=auto \
                    DEPLOY_MEDIAMTX=0 \
                    SKIP_GIT_UPDATE=1 \
                    DEPLOY_BRANCH="$BR" \
                    DEPLOY_PATH="$APP" \
                    bash "$APP/deploy/deploy-all.sh"
                '''
            }
        }
    }

    post {
        success {
            echo 'CI passed.'
        }
        failure {
            echo 'CI failed — check stage logs above.'
        }
    }
}
