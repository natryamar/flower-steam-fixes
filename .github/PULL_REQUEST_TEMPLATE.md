## Summary

<!-- What changes, why is it needed, and which safety/compatibility boundary is affected? -->

## Component

- [ ] Hay-bale installer `1.0.1`
- [ ] Native ScePad bridge component/installer `0.4.5` (unchanged `0.4.4` native artifacts)
- [ ] Install/restore tooling
- [ ] Release bundle `1.2.0` (`v1.2.0`) or click launchers
- [ ] Tests
- [ ] Documentation only

## Validation

<!-- Check only commands actually run. Explain skipped or unavailable checks below. -->

- [ ] `python3 -m unittest discover -s tests -v`
- [ ] `python3 gyro_bridge/build.py --verify-release`
- [ ] `python3 gyro_bridge/test.py`
- [ ] `python3 gyro_bridge/build.py --verify-release` (again after smoke tests)
- [ ] `python3 tools/build_release.py --ref HEAD --output-dir "<external-empty-dir>"`
- [ ] Relevant manual test described below
- [ ] Not applicable (documentation-only or explained below)

Every bundle release includes the native DLL and requires pinned bridge
verification and the isolated Proton smoke matrix, even with unchanged native
artifacts. Follow [`RELEASING.md`](../RELEASING.md), including signed-tag
packaging and manual review gates; passing CI or development packaging is not
publication approval.

### Results and environment

<!-- Include exact commands/results and OS, Proton/toolchain, and controller scope. Native Windows is currently unverified. Do not generalize one device test into hardware certification. -->

## Safety and legal checklist

- [ ] The change remains limited to Flower Steam build `4354278` / App `966330`, or the compatibility expansion is explicitly justified and tested.
- [ ] Exact hashes, no-clobber backup rules, atomic replacement, rollback, and fail-closed behavior were not weakened.
- [ ] Steam controller profiles remain explicit user-owned choices and are not created, selected, edited, or deleted.
- [ ] Native Steam-owned state remains a complete snapshot with whole-provider original fallback; fields are not blended.
- [ ] Tests use only synthetic files and independently written fake DLLs, never a real game installation or Proton prefix.
- [ ] No proprietary game asset, controller profile, log, crash dump, generated `re-temp/` content, absolute personal path, or account/device ID is included.
- [ ] Public behavior, compatibility, version, and troubleshooting documentation is updated where needed.
- [ ] I reviewed [`CONTRIBUTING.md`](../CONTRIBUTING.md) and will report vulnerabilities through the private process in [`SECURITY.md`](../SECURITY.md).

## Additional notes

<!-- Risks, rollback behavior, manual validation limits, or follow-up work. -->
