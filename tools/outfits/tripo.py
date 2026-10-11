"""Submit and collect recorded Tripo image-to-model jobs without automatic resubmission."""
import argparse
import hashlib
import json
import shutil
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
API = 'https://openapi.tripo3d.ai/v3'


def save(path, record):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def api(key, method, endpoint, **kwargs):
    headers = {'Authorization': 'Bearer ' + key}
    data = None
    if 'json' in kwargs:
        data = json.dumps(kwargs['json']).encode()
        headers['Content-Type'] = 'application/json'
    if 'files' in kwargs:
        name, file, mime = kwargs['files']['file']
        boundary = uuid.uuid4().hex
        data = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                f'filename="{name}"\r\nContent-Type: {mime}\r\n\r\n').encode()
        data += file.read() + f'\r\n--{boundary}--\r\n'.encode()
        headers['Content-Type'] = 'multipart/form-data; boundary=' + boundary
    request = urllib.request.Request(API + endpoint, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'HTTP {error.code}: {error.read().decode()[:1000]}') from None
    if result.get('code') != 0:
        raise RuntimeError(json.dumps(result))
    return result['data']


def submit(config, record_path, key):
    images = config.get('images')
    if images is not None:
        views = [image['view'] for image in images]
        if (not 2 <= len(views) <= 4 or 'front' not in views
                or len(set(views)) != len(views)
                or not set(views) <= {'front', 'left', 'back', 'right'}):
            raise ValueError('Multiview inputs require front and unique valid views')
    else:
        images = [config['image']]
    for reference in images:
        if digest(ROOT / reference['path']) != reference['sha256']:
            raise RuntimeError('Input image hash changed')
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record = {'config': config, 'status': 'PREPARING'}
    with record_path.open('x') as file:
        json.dump(record, file, indent=2)
    record['balance_before'] = api(key, 'GET', '/account/balance')
    if record['balance_before']['balance'] < config['estimated_credits']:
        record['status'] = 'INSUFFICIENT_BALANCE'
        save(record_path, record)
        raise RuntimeError('Insufficient balance')
    inputs = []
    for reference in images:
        image = ROOT / reference['path']
        with image.open('rb') as file:
            uploaded = api(key, 'POST', '/files', files={'file': (image.name, file, 'image/png')})
        if 'images' in config:
            inputs.append({reference['view']: uploaded['file_token']})
            record['file_tokens'] = inputs
        else:
            record['file_token'] = uploaded['file_token']
        save(record_path, record)
    if 'images' in config:
        request = {**config['parameters'], 'inputs': inputs}
        endpoint = '/generation/multiview-to-model'
    else:
        request = {**config['parameters'], 'input': record['file_token']}
        endpoint = '/generation/image-to-model'
    record['endpoint'] = endpoint
    record['request'] = request
    record['status'] = 'SUBMITTING'
    save(record_path, record)
    result = api(key, 'POST', endpoint, json=request)
    record['task_id'] = result['task_id']
    record['status'] = 'SUBMITTED'
    save(record_path, record)
    print(json.dumps({'status': record['status'], 'task_id': record['task_id']}))


def poll(record_path, key):
    record = json.loads(record_path.read_text())
    result = api(key, 'GET', '/tasks/' + record['task_id'])
    record['task'] = result
    record['status'] = result['status']
    record['balance_latest'] = api(key, 'GET', '/account/balance')
    save(record_path, record)
    print(json.dumps({k: result[k] for k in
                      ['task_id', 'status', 'progress', 'credits_consumed', 'consumed_credit',
                       'error_code', 'error_message'] if k in result}))
    print(json.dumps({'balance': record['balance_latest'],
                      'output_keys': list(result.get('output', {}))}))


def urls(value, prefix=''):
    if isinstance(value, dict):
        for name, item in value.items():
            yield from urls(item, prefix + ('_' if prefix else '') + name)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from urls(item, prefix + '_' + str(index))
    elif isinstance(value, str) and value.startswith('https://'):
        yield prefix, value


def collect(record_path):
    record = json.loads(record_path.read_text())
    if record['status'] != 'success':
        raise RuntimeError('Task has not completed successfully')
    output = ROOT / record['config']['output_dir']
    output.mkdir(parents=True, exist_ok=True)
    files = record.setdefault('files', {})
    for name, url in urls(record['task'].get('output', {})):
        suffix = Path(urlparse(url).path).suffix or '.bin'
        filename = ''.join(c if c.isalnum() or c in '-_' else '_' for c in name) + suffix
        target = output / filename
        if name in files:
            existing = ROOT / files[name]['path']
            if existing.exists() and digest(existing) == files[name]['sha256']:
                continue
        temporary = target.with_suffix(target.suffix + '.part')
        with urllib.request.urlopen(url, timeout=120) as response:
            with temporary.open('wb') as file:
                shutil.copyfileobj(response, file)
        with temporary.open('rb') as file:
            signature = file.read(8)
        if signature == b'\x89PNG\r\n\x1a\n':
            target = target.with_suffix('.png')
        temporary.replace(target)
        files[name] = {'path': str(target.relative_to(ROOT)), 'bytes': target.stat().st_size,
                       'sha256': digest(target)}
        save(record_path, record)
    print(json.dumps(files, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['submit', 'poll', 'collect'])
    parser.add_argument('config')
    args = parser.parse_args()
    config = json.loads((ROOT / args.config).read_text())
    record_path = ROOT / config['record']
    if args.action == 'collect':
        collect(record_path)
        return
    if args.action == 'submit' and record_path.exists():
        raise SystemExit('Existing record: refusing duplicate submission; use poll/collect')
    key = Path.home().joinpath('.config/tripo/key').read_text().strip()
    if not key:
        raise RuntimeError('Tripo key file is empty')
    try:
        if args.action == 'submit':
            submit(config, record_path, key)
        else:
            poll(record_path, key)
    except Exception as error:
        raise SystemExit(str(error).replace(key, '[REDACTED]')) from None


if __name__ == '__main__':
    main()
