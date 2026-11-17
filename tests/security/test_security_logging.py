"""Local logging controls; no collector, S3 credentials or network required."""

import errno
import json
import logging
import os
from pathlib import Path
import stat
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.utils import audit


def records(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_success_and_failure_are_attributed_without_credentials(client, make_user, login, security_log_path):
    user = make_user()
    tokens = login(user)
    client.get('/admin/users', headers={'Authorization': f"Bearer {tokens['access_token']}"})
    client.post('/token?code=QUERY_SECRET', data={'username': 'unknown-user', 'password': 'BODY_SECRET'},
                headers={'X-Forwarded-For': '198.51.100.99', 'X-Request-ID': 'forged-id'})
    items = records(security_log_path)
    success = next(x for x in items if x['what']['event'] == 'login_succeeded')
    assert success['who']['id'] == str(user.id)
    assert success['who']['type'] == 'user'
    assert success['where']['route'] == '/token'
    assert success['when']['timestamp'].endswith('+00:00')
    assert success['when']['request_id']
    denied = next(x for x in items if x['what']['event'] == 'authz_denied')
    summary = next(x for x in items if x['when']['request_id'] == denied['when']['request_id'] and x['what']['event'] == 'request_rejected')
    # FastAPI dependencies run in worker threads; the actor must flow back.
    assert summary['who']['id'] == str(user.id)
    failure = next(x for x in items if x['what']['event'] == 'login_failed')
    assert failure['who']['type'] == 'anonymous'
    assert failure['who']['source_ip'] == 'testclient'
    raw = security_log_path.read_text()
    for secret in ['QUERY_SECRET', 'BODY_SECRET', 'unknown-user', 'forged-id', '198.51.100.99', tokens['access_token'], tokens['refresh_token']]:
        assert secret not in raw


def test_unmatched_paths_and_validation_errors_do_not_leak_input(client, security_log_path):
    client.get('/secret-in-path?token=secret-in-query')
    client.post('/token', data={'password': 'secret-in-body'})
    items = records(security_log_path)
    assert any(x['where']['route'] == '<unmatched>' and x['what']['details']['status'] == 404 for x in items if x['what']['event'] == 'request_rejected')
    assert 'secret-in-' not in security_log_path.read_text()


def test_event_allowlist_injection_unicode_and_subject_is_not_actor(security_log_path):
    audit.security_event('verification_email_sent', user_id='target-account', reason='hello\r\nforged', password='DO_NOT_LOG', token='DO_NOT_LOG')
    item = records(security_log_path)[0]
    assert item['who']['id'] != 'target-account'
    assert item['what']['details']['reason'] == 'hello??forged'
    assert 'DO_NOT_LOG' not in security_log_path.read_text()
    audit.security_event('oversized', **{key: '😀' * 1000 for key in audit.FIELDS - {'actor'}})
    assert len(security_log_path.read_bytes().splitlines()[1]) < 8192
    assert records(security_log_path)[1]['what']['details']['reason'] == 'event_fields_exceeded_limit'


def log_line(handler, message):
    handler.handle(logging.LogRecord('test', logging.INFO, '', 1, message, (), None))


def test_rotation_is_byte_bounded_and_retains_latest(tmp_path):
    path = tmp_path / 'security.log'
    handler = audit.SecurityFileHandler(path, 50, segment_bytes=1024)
    handler.files = 5  # exercise the production five-segment algorithm cheaply
    for i in range(30):
        log_line(handler, json.dumps({'index': i, 'data': 'a' * 700}))
    files = list(tmp_path.glob('security.log*'))
    assert len(files) == 5
    assert sum(p.stat().st_size for p in files) <= 5 * 1024
    assert all(p.stat().st_size <= 1024 for p in files)
    assert records(path)[-1]['index'] == 29
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o640 for p in files)
    # A new process/handler reopens existing files and continues the same ring.
    replacement = audit.SecurityFileHandler(path, segment_bytes=1024)
    replacement.files = 5
    log_line(replacement, json.dumps({'index': 30, 'data': 'b' * 700}))
    assert records(path)[0]['index'] == 30


def test_separate_writers_share_a_rotation_lock(tmp_path):
    path = tmp_path / 'security.log'
    handlers = [audit.SecurityFileHandler(path, segment_bytes=1024) for _ in range(4)]
    for handler in handlers:
        handler.files = 5
    def write(index):
        for n in range(100):
            log_line(handlers[index], json.dumps({'writer': index, 'n': n}))
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(write, range(4)))
    for path in tmp_path.glob('security.log*'):
        assert path.stat().st_size <= 1024
        records(path)  # no interleaved or torn JSON lines
    assert not any(h.failures for h in handlers)


@pytest.mark.parametrize('error', [errno.ENOSPC, errno.EACCES])
def test_logging_failures_are_fail_open_and_alarm_is_throttled(tmp_path, monkeypatch, capsys, error):
    handler = audit.SecurityFileHandler(tmp_path / 'security.log')
    def fail(*args):
        raise OSError(error, 'SECRET_EXCEPTION_DETAIL')
    monkeypatch.setattr(handler, '_open', fail)
    for _ in range(3):
        log_line(handler, 'SECRET_EVENT')
    assert handler.failures == 3
    output = capsys.readouterr().err
    assert output.count('SECURITY_LOG_WRITE_FAILED') == 1
    assert 'SECRET' not in output


def test_symlink_and_hardlink_targets_are_not_written(tmp_path):
    victim = tmp_path / 'victim'
    victim.write_text('unchanged')
    path = tmp_path / 'security.log'
    handler = audit.SecurityFileHandler(path)
    path.symlink_to(victim)
    log_line(handler, 'evil')
    path.unlink()
    os.link(victim, path)
    log_line(handler, 'evil')
    assert victim.read_text() == 'unchanged'
    assert handler.failures == 2


def test_total_budget_configuration_rejects_unbounded_values():
    from app.config import Settings
    from pydantic import ValidationError
    for value in [0, -1, 51, 500]:
        with pytest.raises(ValidationError):
            Settings(SECURITY_LOG_TOTAL_MIB=value)


def test_partial_disk_full_write_does_not_corrupt_the_next_event(tmp_path, monkeypatch):
    path = tmp_path / 'security.log'
    handler = audit.SecurityFileHandler(path)
    real_write = os.write
    calls = 0
    def partial_then_full(fd, data):
        nonlocal calls
        calls += 1
        if calls == 1:
            return real_write(fd, data[:5])
        raise OSError(errno.ENOSPC, 'full')
    with monkeypatch.context() as patch:
        patch.setattr(os, 'write', partial_then_full)
        log_line(handler, '{"event":"lost"}')
    log_line(handler, '{"event":"recovered"}')
    assert records(path) == [{'event': 'recovered'}]
    assert handler.failures == 1
