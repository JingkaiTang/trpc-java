#!/usr/bin/env python3
"""Run one existing patched starter binary with three Jackson versions and original-starter controls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--maven-repo', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--build-report', required=True, type=Path, help='Surefire XML from the verified starter compatibility build')
args = parser.parse_args()
repo = args.maven_repo.resolve()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
here = Path(__file__).resolve().parent
report = args.build_report.resolve()
properties = {p.attrib['name']: p.attrib['value'] for p in ET.parse(report).findall('./properties/property')}
# Reuse the verified build dependency graph, but exclude all Jackson modules and local classes.
classpath = [p for p in properties['java.class.path'].split(os.pathsep)
             if p.endswith('.jar') and '/com/fasterxml/jackson/' not in p
             and '/trpc-spring-boot-starter/' not in p]
candidate = repo / 'com/tencent/trpc/trpc-spring-boot-starter/2.0.5-peacock3-restart-SNAPSHOT/trpc-spring-boot-starter-2.0.5-peacock3-restart-SNAPSHOT.jar'
original = repo / 'com/tencent/trpc/trpc-spring-boot-starter/2.0.5/trpc-spring-boot-starter-2.0.5.jar'
assert candidate.is_file() and original.is_file()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def jackson(version):
    paths = []
    for artifact in ['jackson-core', 'jackson-databind', 'jackson-annotations']:
        actual_version = '2.21' if artifact == 'jackson-annotations' and version == '2.21.4' else version
        rel = f'com/fasterxml/jackson/core/{artifact}/{actual_version}/{artifact}-{actual_version}.jar'
        path = repo / rel
        if not path.is_file():
            path = out / 'downloads' / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            url = 'https://repo.maven.apache.org/maven2/' + rel
            if not path.is_file():
                path.write_bytes(urllib.request.urlopen(url, timeout=60).read())
            expected = urllib.request.urlopen(url + '.sha1', timeout=60).read().decode().split()[0]
            assert hashlib.sha1(path.read_bytes()).hexdigest() == expected
        paths.append(path)
    return paths

versions = ['2.15.2', '2.18.2', '2.21.4']
libs = {v: jackson(v) for v in versions}
classes = out / 'classes'
classes.mkdir(exist_ok=True)
# Compile probe once, then run the identical probe and identical candidate jar in separate JVMs.
cp = os.pathsep.join([str(candidate), *map(str, libs['2.21.4']), *classpath])
subprocess.run(['java', '-version'], check=True)
subprocess.run(['javac', '-cp', cp, '-d', str(classes), str(here / 'JacksonBindingProbe.java')], check=True)
results = []
configs = []
for version in versions:
    for label, starter in [('patched', candidate), ('original', original)]:
        cp = os.pathsep.join([str(classes), str(starter), *map(str, libs[version]), *classpath])
        run = subprocess.run(['java', '-cp', cp, 'JacksonBindingProbe', version], text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out / f'{label}-{version}.log').write_text(run.stdout)
        expected_failure = label == 'original' and version == '2.21.4'
        if expected_failure:
            assert run.returncode != 0 and 'NoSuchFieldError' in run.stdout and 'SNAKE_CASE' in run.stdout, run.stdout
        else:
            assert run.returncode == 0 and 'BINDING_PROBE_SUCCESS' in run.stdout, run.stdout
            configs.append(next(l.removeprefix('CONFIG_JSON ') for l in run.stdout.splitlines() if l.startswith('CONFIG_JSON ')))
        results.append({'starter': label, 'jackson': version, 'returncode': run.returncode,
                        'expected_failure': expected_failure, 'starter_sha256': sha(starter),
                        'jackson_jars': [{'path': str(p), 'sha256': sha(p)} for p in libs[version]]})
        print(label, version, 'EXPECTED_FAILURE' if expected_failure else 'PASS', flush=True)
assert len(set(configs)) == 1, 'Configuration differs between versions or patched/original starter'
(out / 'results.json').write_text(json.dumps({'runs': results, 'all_successful_configurations_equal': True,
    'scope': 'Configuration-to-Map binding only; same Java 21 binary, not full Boot or Java 8/17 validation'}, indent=2) + '\n')
(out / 'configuration.json').write_text(configs[0] + '\n')
