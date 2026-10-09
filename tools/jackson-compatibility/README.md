# Jackson configuration binding compatibility

Source baseline: `JDK17/Springboot3`, v2.0.5 (`6d2a46043757c3053745beaecbae9f7ebd0b9a83`). The production change lives in `trpc-spring-boot-starters/trpc-spring-boot-starter`; `jackson-naming.patch` records the minimal change for source verification.

`build.py` verifies the module against the pinned source plus the reviewed patch, then builds using an explicitly supplied consumer compatibility POM. It accepts a descendant commit only when every original module file still matches the pinned source plus the patch. This is a targeted compatibility harness, not the upstream reactor build or upstream full test suite.

The consumer POM must use `${trpc.source.dir}/src/main/java`, `${trpc.source.dir}/src/main/resources` and `${trpc.compatibility.dir}/src/test/java`. It owns dependency versions, candidate artifact coordinates, compiler target and packaging. No consumer-specific parent POM is copied into this repository.

```sh
python3 tools/jackson-compatibility/build.py \
  --build-pom /path/to/consumer-compatibility/pom.xml \
  --maven-repo /path/to/task-maven-repository --offline
python3 tools/jackson-compatibility/compatibility/run-matrix.py \
  --build-report /path/to/consumer-compatibility/target/surefire-reports/TEST-com.tencent.trpc.spring.boot.starters.ConfigurationBindingTest.xml \
  --maven-repo /path/to/task-maven-repository --output /path/to/matrix-output
```

The current matrix uses the local candidate `2.0.5-peacock3-restart-SNAPSHOT` and official `2.0.5` as control. It tests one identical candidate binary with Jackson 2.15.2, 2.18.2 and 2.21.4, asserts exact configuration fields and compares complete output. It downloads missing Jackson jars from Maven Central into the output directory and verifies their published checksums. It starts no listeners and calls no business services. Java 21 is required by the current candidate binary; passing these checks does not certify old JDKs or complete applications.

Use the actual production source as the implementation. Do not add duplicate classes to consumer applications. This tooling is local maintenance only; no upstream PR or artifact publication is implied.
