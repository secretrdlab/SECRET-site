// Jenkins pipeline for the SECRET website.
//
// Every push: validate BibTeX -> build with Hugo -> check links -> archive the site.
// Pushes to the main branch are also deployed (see the Deploy stage).
//
// Requirements on the agent: bash, curl, tar, python3 (with venv), rsync + ssh (for deploy).
// Hugo is downloaded and cached automatically — no Jenkins plugins beyond the defaults
// (Pipeline, Git, Credentials Binding) are needed.

pipeline {
  agent any

  options {
    timestamps()
    timeout(time: 20, unit: 'MINUTES')
    buildDiscarder(logRotator(numToKeepStr: '30'))
    disableConcurrentBuilds()
  }

  // Prefer a webhook from GitLab/GitHub; polling is the fallback if webhooks aren't possible.
  triggers {
    pollSCM('H/5 * * * *')
  }

  parameters {
    booleanParam(name: 'FORCE_DEPLOY', defaultValue: false, description: 'Deploy even if this is not the main branch')
  }

  environment {
    HUGO_VERSION   = '0.152.2'
    HUGO_ENV       = 'production'
    // --- Deploy target: change these to match your web server ---
    DEPLOY_HOST    = 'secret.inf.ufpr.br'          // server that serves the site
    DEPLOY_USER    = 'deploy'                      // ssh user on that server
    DEPLOY_PATH    = '/var/www/secret.seg.br/'     // web root (trailing slash matters for rsync)
    DEPLOY_CRED_ID = 'secret-site-deploy-key'      // Jenkins "SSH Username with private key" credential
    TOOLS          = "${WORKSPACE}/.tools"
    // Homebrew paths are included because Jenkins on macOS starts with a minimal PATH.
    PATH           = "${WORKSPACE}/.tools/bin:${WORKSPACE}/.venv/bin:/opt/homebrew/bin:/usr/local/bin:${env.PATH}"
  }

  stages {
    stage('Setup') {
      steps {
        sh '''
          set -eu
          mkdir -p "$TOOLS/bin"
          if ! "$TOOLS/bin/hugo" version 2>/dev/null | grep -q "v${HUGO_VERSION}"; then
            # Pick the right Hugo build for this agent (macOS or Linux, Intel or ARM).
            case "$(uname -s)-$(uname -m)" in
              Darwin-*)        PKG=darwin-universal ;;
              Linux-x86_64)    PKG=linux-amd64 ;;
              Linux-aarch64|Linux-arm64) PKG=linux-arm64 ;;
              *) echo "Unsupported platform: $(uname -s)-$(uname -m)"; exit 1 ;;
            esac
            echo "Installing Hugo ${HUGO_VERSION} (${PKG})"
            curl -fsSL -o "$TOOLS/hugo.tgz" \
              "https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_extended_${HUGO_VERSION}_${PKG}.tar.gz"
            tar -xzf "$TOOLS/hugo.tgz" -C "$TOOLS/bin" hugo
            rm -f "$TOOLS/hugo.tgz"
          fi
          hugo version
          [ -x .venv/bin/python ] || python3 -m venv .venv
          .venv/bin/pip install --quiet --upgrade pip
          .venv/bin/pip install --quiet -r requirements.txt
        '''
      }
    }

    stage('Validate BibTeX') {
      steps {
        // Fails the build on duplicate keys, missing required fields or bad years.
        sh 'python scripts/bib2data.py --check'
      }
    }

    stage('Build') {
      steps {
        sh '''
          set -eu
          python scripts/bib2data.py
          rm -rf public
          hugo --gc --minify --panicOnWarning
        '''
      }
    }

    stage('Check') {
      steps {
        sh 'python scripts/check_site.py public'
      }
    }

    stage('Archive') {
      steps {
        sh 'tar -czf site.tar.gz -C public .'
        archiveArtifacts artifacts: 'site.tar.gz', fingerprint: true
      }
    }

    stage('Deploy') {
      when {
        anyOf {
          branch 'main'
          expression { return params.FORCE_DEPLOY }
          // Non-multibranch jobs don't set BRANCH_NAME; fall back to GIT_BRANCH.
          expression { return env.BRANCH_NAME == null && (env.GIT_BRANCH ?: '').endsWith('main') }
        }
      }
      steps {
        withCredentials([sshUserPrivateKey(credentialsId: env.DEPLOY_CRED_ID, keyFileVariable: 'SSH_KEY')]) {
          sh '''
            set -eu
            rsync -az --delete --checksum \
              -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
              public/ "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}"
          '''
        }
      }
    }
  }

  post {
    failure {
      echo 'Build failed. Check the "Validate BibTeX" stage first — most failures are a typo in bibliography/*.bib.'
    }
  }
}
