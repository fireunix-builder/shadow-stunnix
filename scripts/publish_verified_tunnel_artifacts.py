"""Publish hash-pinned binary artifacts without rebuilding private source."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-root', type=Path, default=Path('incoming'))
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    manifest_path = Path(__file__).resolve().parents[1] / 'release-manifests/tunnel-reliability-2026-09-12.json'
    manifest = json.loads(manifest_path.read_text())
    verified = []
    for release in manifest:
        found = {}
        for path in (args.input_root / release['service']).rglob('*'):
            if path.is_file() and path.name.endswith(('.tar.gz', '.zip')):
                if path.name in found:
                    raise RuntimeError('Duplicate archive: ' + path.name)
                found[path.name] = path
        if set(found) != set(release['files']):
            raise RuntimeError('Archive inventory mismatch: ' + release['service'])
        for name, expected in release['files'].items():
            if hashlib.sha256(found[name].read_bytes()).hexdigest() != expected:
                raise RuntimeError('Archive SHA256 mismatch: ' + name)
        verified.append((release, found))
        print(release['service'], 'verified', len(found), 'archives', flush=True)
    if args.verify_only:
        return
    for variable in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'R2_ACCOUNT_ID', 'R2_BUCKET', 'R2_PUBLIC_URL']:
        if not os.environ.get(variable):
            raise RuntimeError('Missing setting: ' + variable)
    bucket = os.environ['R2_BUCKET']
    public = os.environ['R2_PUBLIC_URL'].rstrip('/')
    if bucket != 'shadow' or public != 'https://release.xtunnel.app':
        raise RuntimeError('R2 destination does not match the reviewed bucket/domain')
    endpoint = 'https://' + os.environ['R2_ACCOUNT_ID'] + '.r2.cloudflarestorage.com'
    if not shutil.which('aws'):
        raise RuntimeError('AWS CLI is required on the build runner')

    def aws(*command):
        return subprocess.check_output(['aws', '--endpoint-url', endpoint, *command], text=True)

    def upload(path, key, content_type, cache):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        aws('s3api', 'put-object', '--bucket', bucket, '--key', key,
            '--body', str(path), '--content-type', content_type,
            '--cache-control', cache, '--metadata', 'sha256=' + digest)
        head = json.loads(aws('s3api', 'head-object', '--bucket', bucket, '--key', key))
        if head['ContentLength'] != path.stat().st_size or head['Metadata'].get('sha256') != digest:
            raise RuntimeError('Uploaded object verification failed: ' + key)
        print('Uploaded and verified:', key, flush=True)

    with tempfile.TemporaryDirectory(prefix='verified-releases-') as temporary:
        latest = []
        for release, found in verified:
            service, version = release['service'], release['version']
            prefix = service + '/' + version
            target = Path(temporary) / service
            target.mkdir()
            files = {}
            checksums = []
            filename_prefix = ('shadow-control' if service == 'Control' else service.lower()) + '-' + version.removeprefix('v') + '-'
            for name, path in sorted(found.items()):
                if not name.startswith(filename_prefix):
                    raise RuntimeError('Archive version mismatch: ' + name)
                digest = release['files'][name]
                checksums.append(digest + '  ' + name)
                platform = name.removeprefix(filename_prefix).removesuffix('.tar.gz').removesuffix('.zip')
                files[platform] = {'url': public + '/' + prefix + '/' + name, 'sha256': digest}
                upload(path, prefix + '/' + name, 'application/zip' if name.endswith('.zip') else 'application/gzip', 'public,max-age=31536000,immutable')
            for arch in ['amd64', 'arm64']:
                if 'linux-' + arch in files:
                    files[arch] = files['linux-' + arch]
            checksum_file = target / 'SHA256SUMS'
            checksum_file.write_text('\n'.join(checksums) + '\n')
            upload(checksum_file, prefix + '/SHA256SUMS', 'text/plain', 'public,max-age=31536000,immutable')
            payload = {'version': version, 'released_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       'files': files, 'checksums_url': public + '/' + prefix + '/SHA256SUMS'}
            metadata = target / 'release.json'
            metadata.write_text(json.dumps(payload, indent=2) + '\n')
            upload(metadata, prefix + '/release.json', 'application/json', 'public,max-age=31536000,immutable')
            latest.append((metadata, service + '/latest.json'))
        # Expose the new versions only after every reviewed archive is present.
        for metadata, key in latest:
            upload(metadata, key, 'application/json', 'no-cache,max-age=0')


if __name__ == '__main__':
    main()
