#!/usr/bin/env python3
"""Build a local candidate from the pinned, otherwise unmodified upstream checkout."""
import argparse
from pathlib import Path
import subprocess

BASE = "6d2a46043757c3053745beaecbae9f7ebd0b9a83"
MODULE = "trpc-spring-boot-starters/trpc-spring-boot-starter"
FILE = MODULE + "/src/main/java/com/tencent/trpc/spring/boot/starters/context/configuration/bind/TRpcConfigurationBindResult.java"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source-checkout", type=Path, default=Path(__file__).resolve().parents[2])
parser.add_argument("--build-pom", required=True, type=Path, help="Consumer compatibility POM; must declare source/test directories via the supplied properties")
parser.add_argument("--maven-repo", required=True, type=Path)
parser.add_argument("--offline", action="store_true")
args = parser.parse_args()
source = args.source_checkout.resolve()
here = Path(__file__).resolve().parent

def git(*args):
    return subprocess.check_output(["git", "-C", str(source), *args])

if subprocess.run(["git", "-C", str(source), "merge-base", "--is-ancestor", BASE, "HEAD"]).returncode != 0:
    raise SystemExit("Refusing to build: checkout does not descend from the pinned v2.0.5 commit")
if git("diff", "--cached", "--", MODULE) or git("ls-files", "--others", MODULE):
    raise SystemExit("Refusing staged changes or extra untracked module sources")
patch = (here / "jackson-naming.patch").read_bytes()
diff = git("diff", "--no-ext-diff", BASE, "--", MODULE)
if not diff:
    subprocess.run(["git", "-C", str(source), "apply", "--check", str(here / "jackson-naming.patch")], check=True)
    subprocess.run(["git", "-C", str(source), "apply", str(here / "jackson-naming.patch")], check=True)
    diff = git("diff", "--no-ext-diff", BASE, "--", MODULE)
if diff != patch:
    raise SystemExit("Refusing to build: checkout changes differ from the reviewed patch")
# Verify all module files, including files hidden by skip-worktree/assume-unchanged flags.
for raw in git("ls-tree", "-r", "--name-only", "-z", BASE, MODULE, "LICENSE", "NOTICE").split(b"\0"):
    if not raw:
        continue
    name = raw.decode()
    expected = git("show", BASE + ":" + name)
    if name == FILE:
        expected = expected.replace(b"import com.fasterxml.jackson.databind.PropertyNamingStrategy;",
                                    b"import com.fasterxml.jackson.databind.PropertyNamingStrategies;")
        expected = expected.replace(b"PropertyNamingStrategy.SNAKE_CASE", b"PropertyNamingStrategies.SNAKE_CASE")
    if (source / name).read_bytes() != expected:
        raise SystemExit("Source mismatch: " + name)
subprocess.run(["java", "-version"], check=True)
command = ["mvn", "-B", "-ntp", "-f", str(args.build_pom.resolve()),
           "-Dtrpc.source.dir=" + str(source / MODULE),
           "-Dtrpc.compatibility.dir=" + str(here),
           "-Dmaven.repo.local=" + str(args.maven_repo.resolve()), "clean", "install"]
if args.offline:
    command.insert(1, "-o")
subprocess.run(command, check=True)
