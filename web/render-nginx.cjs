// Match the CSP to the same build-time API origin as the frontend bundle.
const fs = require('node:fs');
const url = new URL(process.env.VUE_APP_API_URL);
if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
  throw new Error('VUE_APP_API_URL must be an HTTP(S) URL without credentials');
}
fs.writeFileSync('nginx.rendered.conf',
  fs.readFileSync('nginx.conf.template', 'utf8').replaceAll('${API_ORIGIN}', url.origin));
