pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        BASE_URL = 'https://api-staging.spontansolutions.com'
        TEST_PRODUCT_SKU = 'DELL-Pro'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup Python Environment') {
            steps {
                sh '''
                    python3 -m venv .venv
                    .venv/bin/python -m pip install --upgrade pip
                    .venv/bin/python -m pip install -r requirements.txt
                '''
            }
        }

        stage('API Integration Tests') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'staging-integration-customer',
                        usernameVariable: 'TEST_CUSTOMER_USERNAME',
                        passwordVariable: 'TEST_CUSTOMER_PASSWORD'
                    ),
                    usernamePassword(
                        credentialsId: 'staging-integration-admin',
                        usernameVariable: 'TEST_ADMIN_USERNAME',
                        passwordVariable: 'TEST_ADMIN_PASSWORD'
                    )
                ]) {
                    sh '''
                        mkdir -p reports

                        .venv/bin/python -m pytest -v \
                          tests/test_ecommerce_flow.py \
                          --junitxml=reports/integration-results.xml
                    '''
                }
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true,
                  testResults: 'reports/*.xml'
        }

        success {
            echo 'STAGING integration tests PASSED'
        }

        failure {
            echo 'STAGING integration tests FAILED'
        }
    }
}