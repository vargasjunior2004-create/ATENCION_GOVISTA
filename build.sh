echo "Compilando frontend..."
node --version
npm --version

(
  cd frontend
  npm ci
  BUILD_PATH=../frontend_build npm run build
)

FRONTEND_JS=$(sed -n 's|.*"main.js": "/static/js/\([^"]*\)".*|\1|p' frontend_build/asset-manifest.json)
FRONTEND_CSS=$(sed -n 's|.*"main.css": "/static/css/\([^"]*\)".*|\1|p' frontend_build/asset-manifest.json)

test -n "$FRONTEND_JS"
test -n "$FRONTEND_CSS"
test -f "frontend_build/static/js/$FRONTEND_JS"
test -f "frontend_build/static/css/$FRONTEND_CSS"