# Release process

<!-- markdownlint-disable MD013 -->

## Versioning

The project uses Semantic Versioning. Before 1.0 both the C API and the persisted
settings are allowed to change, but stable setting IDs are still preferred.
`.version` and `.id` of the filter must never change without a migration.

## Continuous integration

| Workflow | Trigger | Purpose |
|---|---|---|
| `build.yml` | push, pull request, tags | configure, build, install and upload the Windows x64 archive |
| `checks.yml` | push, pull request | clang-format 19 check and libobs-free unit tests |
| `release.yml` | tags | build, package, checksums and a draft GitHub release |

The Windows build uses the `windows-ci-x64` preset, which turns warnings into
errors.

## Producing the package

~~~powershell
cmake --preset windows-ci-x64
cmake --build --preset windows-x64 --config RelWithDebInfo --parallel
cmake --install build_x64 --config RelWithDebInfo --prefix .\release
Compress-Archive -Path .\release\* -DestinationPath obs-edge-fade-0.1.0-windows-x64.zip
~~~

The archive contains:

~~~text
obs-edge-fade/
  bin/64bit/obs-edge-fade.dll
  bin/64bit/obs-edge-fade.pdb
  data/effects/edge-fade.effect
  data/locale/*.ini
~~~

## Release checklist

1. Update the version in `buildspec.json` and `CHANGELOG.md`.
2. Run the unit tests and the full [manual test plan](manual-test-plan.md);
   record the run with [test-results-template.md](test-results-template.md).
3. Push a semver tag (the release workflow rejects non-semver tags).
4. Let `release.yml` produce the draft release and checksums.
5. Review the draft, then publish.

## Updating the OBS pin

1. Pick the OBS release to target.
2. Update the `obs-studio` version and hash in `buildspec.json`.
3. Update the matching `prebuilt` obs-deps version and hash.
4. Delete `.deps` and reconfigure.
5. Run the full test matrix before tagging.
