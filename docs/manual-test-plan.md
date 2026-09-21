# Manual test plan

<!-- markdownlint-disable MD013 -->

This is the checklist for everything that cannot be verified without a real OBS
Studio instance. Run it on Windows 10/11 x64 against a build of the plugin.

The automated checks (clang-format, unit tests and the Windows build) live in
[testing.md](testing.md) and CI. This plan covers GPU and integration behaviour.

Record the outcome with [test-results-template.md](test-results-template.md).

## 0. Build, install and load

~~~powershell
cmake --preset windows-x64
cmake --build --preset windows-x64 --config RelWithDebInfo --parallel
cmake --install build_x64 --config RelWithDebInfo
~~~

- [ ] The install created
      %ProgramData%\obs-studio\plugins\obs-edge-fade\bin\64bit\obs-edge-fade.dll
      and an obs-edge-fade\data folder next to it.
- [ ] scripts/install-local.ps1 performs the three commands above in one step.
- [ ] Start OBS and open **Help > Log Files > View Current Log**.
- [ ] The log contains [OBS Edge Fade] Plugin loaded (version 0.1.0).
- [ ] The log has no [OBS Edge Fade] error lines about missing effects.

## 1. Registration and lifecycle

- [ ] A video source's **Filters** dialog lists the OBS Edge Fade entry.
- [ ] Add and remove the filter five times; OBS stays responsive.
- [ ] Enable and disable the filter repeatedly; the image toggles cleanly.
- [ ] Duplicate the source and the scene; both copies keep working.
- [ ] Remove the source while the filter is active; no crash.
- [ ] Close OBS with the filter active; it exits without an error dialog.
- [ ] Reopen OBS; the scene reloads with the filter and its settings intact.

## 2. Visual validation (resolve these before anything else)

These confirm the vertical orientation used by "uv * size" in the shader. If a
result is mirrored vertically, stop and report it: the fix is the y term inside
`data/effects/edge-fade.effect`, see [testing.md](testing.md).

- [ ] Edge Fade: **Left** fades the visually left edge.
- [ ] Edge Fade: **Right**, **Top** and **Bottom** each fade their own side.
- [ ] Edge Fade: with **Link sides** enabled, changing one side updates all four.
- [ ] A fade set on one side only does not bleed into the opposite side.

Record any mismatch; nothing below is trustworthy until this section passes.

## 3. Edge Fade

Default settings are all zero, so the filter is a no-op until a side is set.

- [ ] Set only **Left** to 200 on a 1920x1080 source: only the left edge fades
      and the fade is smooth.
- [ ] Repeat for **Right**, **Top** and **Bottom**.
- [ ] Enable **Link sides** and change **Right**: all four sides follow.
- [ ] **Smoothness** 0 vs 100 changes how gradual the transition is.
- [ ] **Curve** Linear, Smooth and Soft each change the falloff shape.
- [ ] With two adjacent sides set, the corner fades without a hard band.
- [ ] No 1 px bright or dark line appears along any edge.
- [ ] Interior alpha is untouched (compare with the filter disabled).
- [ ] Set all four sides back to 0: the image returns to normal (bypass).

## 4. Filter chain

- [ ] Apply a native filter (for example Color Correction) before and after Edge
      Fade; colours and alpha stay correct.
- [ ] Stack two Edge Fade filters on the same source; both render and the image
      stays stable.
- [ ] Apply Edge Fade after a native Chroma Key: the fade follows the alpha the
      source emits.
- [ ] Apply Edge Fade to a nested scene; the fade covers the scene output.

## 5. Resolution and frame rate matrix

Resolutions: 64x64, 320x240, 640x480, 1280x720, 1920x1080, 2560x1440, 3840x2160.
Frame rates: 30, 60, 120 FPS.

- [ ] The filter looks correct at every resolution.
- [ ] 64x64 does not break the fade maths.
- [ ] A fade wider than the source (for example 1000 px on a 320x240 source)
      degrades gracefully instead of producing artefacts.
- [ ] Changing a media or browser source resolution live updates the filter.
- [ ] Nothing depends on the frame rate.

## 6. Colour spaces and HDR

- [ ] SDR source into an SDR canvas looks unchanged around the effect.
- [ ] SDR source into an HDR canvas looks correct.
- [ ] HDR source into an HDR canvas looks correct.
- [ ] Chains with a native HDR filter do not double-convert.

Do not claim HDR support until these pass; see [testing.md](testing.md).

## 7. Performance and leaks

Use **OBS Stats**, Task Manager (GPU engine) and the OBS log; see
[performance.md](performance.md).

- [ ] Edge Fade uses a single GPU pass and no extra buffers.
- [ ] VRAM stays flat while the filter is enabled (nothing is recreated per
      frame).
- [ ] Stress: 10 sources with Edge Fade.
- [ ] Leak loop: create, change settings and delete the filter 100+ times; CPU
      memory, VRAM and handles return to the starting values.

## 8. Failure handling

- [ ] Rename `edge-fade.effect` and restart OBS: the filter bypasses with a
      logged error instead of a black frame or a crash.
- [ ] Move the whole data folder away: the filter bypasses safely.
- [ ] Rapidly drag the sliders: no flicker and no crash.
- [ ] Corrupt a settings value in the scene JSON: the filter clamps it.
