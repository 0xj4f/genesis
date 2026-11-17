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
        "--set-string", f"host={auth_host}", "--set-string", f"corsOrigins[0]=https://{shop_host}",
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


def test_local_log_budget_and_container_isolation(deployment):
    _, _, api, container, documents = deployment
    pod = api["spec"]["template"]["spec"]
    assert pod["securityContext"]["runAsUser"] == 65532
    assert pod["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
    assert pod["automountServiceAccountToken"] is False
    assert len(pod["containers"]) == 1
    assert not pod.get("initContainers")
    assert not any(d['metadata']['name'] == 'genesis-security-collector' for d in documents)
    assert container['securityContext']['readOnlyRootFilesystem'] is True
    assert container['securityContext']['allowPrivilegeEscalation'] is False
    assert container['securityContext']['capabilities']['drop'] == ['ALL']
    volume = next(v for v in pod['volumes'] if v['name'] == 'security-logs')
    assert volume['emptyDir'] == {'medium': 'Memory', 'sizeLimit': '60Mi'}
    assert not any(v['name'] == 'collector-identity' for v in pod['volumes'])


def test_disabled_collector_can_be_rendered_as_placeholder():
    args = ['helm', 'template', 'genesis', str(INFRA / 'public/iam'), '--namespace', 'iam',
            '--set-string', 'host=auth.example.com', '--set-string', 'corsOrigins[0]=https://shop.example.com',
            '--set', 'securityLogging.collector.enabled=true', '--set', 'securityLogging.totalMiB=100',
            '--set-string', 'securityLogging.collector.image=example.invalid/fluent-bit@sha256:' + '0' * 64,
            '--set-string', 'securityLogging.collector.bucket=placeholder-bucket',
            '--set-string', 'securityLogging.collector.region=ap-southeast-1',
            '--set-string', 'securityLogging.collector.roleArn=arn:aws:iam::000000000000:role/placeholder',
            '--set-string', 'securityLogging.collector.serviceAccountName=placeholder']
    docs = list(yaml.safe_load_all(subprocess.run(args, capture_output=True, text=True, check=True).stdout))
    pod = next(d for d in docs if d['kind'] == 'Deployment' and d['metadata']['name'] == 'genesis-api')['spec']['template']['spec']
    api, collector = pod['containers']
    assert not any(m['name'] == 'collector-identity' for m in api['volumeMounts'])
    assert next(m for m in collector['volumeMounts'] if m['name'] == 'security-logs')['readOnly'] is True
    assert next(v for v in pod['volumes'] if v['name'] == 'security-logs')['emptyDir']['sizeLimit'] == '110Mi'
    config = next(d for d in docs if d['kind'] == 'ConfigMap')['data']['fluent-bit.conf']
    assert 'store_dir_limit_size  20M' in config
    assert 'Path              /var/log/security.log' in config
    assert 'tls.verify            On' in config
    # Fail closed instead of accidentally creating an unbounded ring or unreviewed collector.
    for setting in ['securityLogging.totalMiB=500', 'securityLogging.collector.image=fluent/fluent-bit:latest']:
        rejected = subprocess.run(args + ['--set-string', setting], capture_output=True, text=True)
        assert rejected.returncode != 0


def test_app_accepts_chart_hosts_probes_and_cors_in_production(deployment, tmp_path):
    auth_host, shop_host, _, container, _ = deployment
    values = {item["name"]: item["value"] for item in container["env"] if "value" in item}
    private, public = generate_rsa_key_pair()
    (tmp_path / "private.pem").write_bytes(private)
    (tmp_path / "public.pem").write_bytes(public)
    values.update(OAUTH_PRIVATE_KEY_PATH=str(tmp_path / "private.pem"),
                  OAUTH_PUBLIC_KEY_PATH=str(tmp_path / "public.pem"), UPLOAD_DIR=str(tmp_path / "uploads"),
                  SECURITY_LOG_PATH=str(tmp_path / "security.log"))
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
