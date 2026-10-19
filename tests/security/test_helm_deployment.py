"""Optional offline checks against the adjacent Mac mini infrastructure chart."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest
import yaml

from app.auth.keys import generate_rsa_key_pair
from app.config import Settings


ROOT = Path(__file__).resolve().parents[2]
INFRA = Path(os.environ.get("GENESIS_INFRA_ROOT", str(ROOT.parent / "mac-mini-m1-infrastructure")))
pytestmark = pytest.mark.skipif(
    not shutil.which("helm") or not (INFRA / "public/iam/Chart.yaml").is_file(),
    reason="Requires Helm and the adjacent Mac mini infrastructure checkout",
)


@pytest.fixture(params=["dev", "prod"])
def deployment(request):
    config = (INFRA / f"environments/{request.param}.mk").read_text()
    auth_host = re.search(r"^AUTH_HOST\s*:?=\s*(\S+)", config, re.M)[1]
    shop_host = re.search(r"^SHOP_HOST\s*:?=\s*(\S+)", config, re.M)[1]
    rendered = subprocess.run([
        "helm", "template", "genesis", str(INFRA / "public/iam"), "--namespace", "iam",
        "--set-string", f"host={auth_host}", "--set-string", f"shopHost={shop_host}",
        "--set-string", "tag=offline-compatibility-test",
    ], text=True, capture_output=True, check=True)
    documents = list(yaml.safe_load_all(rendered.stdout))
    api = next(d for d in documents if d["kind"] == "Deployment" and d["metadata"]["name"] == "genesis-api")
    container = api["spec"]["template"]["spec"]["containers"][0]
    return auth_host, shop_host, api, container, documents


def test_chart_enables_valid_production_settings_without_new_services(deployment):
    auth_host, shop_host, api, container, documents = deployment
    values = {item["name"]: item["value"] for item in container["env"] if "value" in item}
    settings = Settings(**values, _env_file=None)
    assert settings.ENVIRONMENT == "production"
    assert settings.OAUTH_ISSUER == f"https://{auth_host}"
    assert settings.cors_origins == [f"https://{shop_host}"]
    assert "genesis-api.iam.svc.cluster.local" in settings.allowed_hosts
    assert auth_host in settings.allowed_hosts
    assert "*" not in settings.allowed_hosts
    assert settings.RATE_LIMIT_PER_SECOND == 30
    assert settings.AUTH_RATE_LIMIT_PER_MINUTE == 10
    assert settings.OAUTH_ALGORITHM == "RS256"
    assert api["spec"]["replicas"] == 1
    assert api["spec"]["strategy"]["type"] == "Recreate"
    assert {d["metadata"]["name"] for d in documents if d["kind"] == "Service"} == {"genesis-api", "genesis-db"}
    secret = next(item for item in container["env"] if item["name"] == "BOOTSTRAP_ROOT_PASSWORD")["valueFrom"]["secretKeyRef"]
    assert secret == {"name": "genesis-db", "key": "bootstrap-root-password", "optional": True}


def test_rendered_probe_hosts_match_production_allowlist(deployment):
    auth_host, _, _, container, _ = deployment
    for name in ("startupProbe", "readinessProbe", "livenessProbe"):
        probe = container[name]["httpGet"]
        assert probe["path"] == "/health"
        assert "host" not in probe  # Keep the destination as the pod IP.
        assert probe["httpHeaders"] == [{"name": "Host", "value": auth_host}]
    mount = next(m for m in container["volumeMounts"] if m["name"] == "jwt-keys")
    assert mount["mountPath"] == "/app/keys" and mount["readOnly"] is True


def test_app_accepts_chart_hosts_probes_and_cors_in_production(deployment, tmp_path):
    auth_host, shop_host, _, container, _ = deployment
    values = {item["name"]: item["value"] for item in container["env"] if "value" in item}
    private, public = generate_rsa_key_pair()
    (tmp_path / "private.pem").write_bytes(private)
    (tmp_path / "public.pem").write_bytes(public)
    values.update(OAUTH_PRIVATE_KEY_PATH=str(tmp_path / "private.pem"),
                  OAUTH_PUBLIC_KEY_PATH=str(tmp_path / "public.pem"), UPLOAD_DIR=str(tmp_path / "uploads"))
    script = '''
import os
from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings
settings = get_settings()
with TestClient(app) as client:
    for host in settings.allowed_hosts:
        response = client.get('/health', headers={'Host': host})
        assert response.status_code == 200, (host, response.status_code)
    host = os.environ['TEST_PUBLIC_HOST']
    assert client.get('/health', headers={'Host': 'unexpected.example'}).status_code == 400
    headers = {'Host': host}
    assert client.get('/.well-known/jwks.json', headers=headers).json()['keys'][0]['alg'] == 'RS256'
    assert client.get('/.well-known/openid-configuration', headers=headers).json()['issuer'] == settings.OAUTH_ISSUER
    headers.update(Origin=os.environ['TEST_SHOP_ORIGIN'], **{'Access-Control-Request-Method': 'POST'})
    response = client.options('/token', headers=headers)
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == os.environ['TEST_SHOP_ORIGIN']
    headers['Origin'] = 'https://unexpected.example'
    assert client.options('/token', headers=headers).status_code == 400
print('production startup, public/internal hosts, probes, JWKS and CORS passed')
'''
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env={**os.environ, **values,
        "TEST_PUBLIC_HOST": auth_host, "TEST_SHOP_ORIGIN": f"https://{shop_host}"}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
