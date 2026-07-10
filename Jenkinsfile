// home-camera-monitor — Jenkins Pipeline (primary CI/CD for course scoring)
// Install guide: docs/B组-Jenkins安装指引.md
// Team usage: docs/CI-CD使用说明.md

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
                    DEPLOY_BRANCH="${BRANCH_NAME:-dev}" \
                    DEPLOY_PATH="${DEPLOY_PATH}" \
                    bash "${DEPLOY_PATH}/deploy/deploy-all.sh"
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
