# TNG Boxing — Unity 6 migration source

**Status: source project, not an Editor-compiled or play-tested Unity release.** The managed cloud workspace has no Unity Editor, Web Build Support, Android Build Support or activated Unity license. The current production Three.js game remains available. Unity requires a valid license; its license eligibility and any fees are determined by Unity. No license, studio account or commercial asset purchase has been made.

This initial Unity implementation includes the existing CC0 9,055-vertex/19-bone skinned athlete, generated gloves/boots, procedural boxing poses, a ring with ropes/corner posts, dynamic lighting, broadcast camera, opponent telegraphs/guard/pressure, stamina/recovery, impact-time range checks, four modes (sparring, heavy bag, defense/counters, combination lab), local sound, a round HUD, touch movement pad and independent punch/held-guard controls. It is an engineering foundation, not a finished photorealistic/motion-captured sports game. Footwork challenges, custom combinations and gamepad support remain available in the existing web version; they have not yet been ported to Unity. Licensed motion capture, facial/cloth art, camera polish, hit detection/animation tuning and actual device profiling remain further development work.

## Windows setup (PowerShell)

1. Install Unity Hub from https://unity.com/download and sign in privately. Activate the appropriate Unity license in Hub.
2. In Hub → Installs → Install Editor, install **Unity 6 LTS 6000.0.32f1**, or use the same Unity 6 LTS patch for the entire team. Include **Web Build Support**. For APK builds, include **Android Build Support, SDK/NDK Tools and OpenJDK**.
3. Add/open `unity/TngBoxing` as a project. Let asset import finish. This project uses the built-in rendering pipeline; no paid models or GLB-import plugin is required.
4. Press Play in any scene. A runtime initializer creates the arena. Resolve any Editor compilation/import errors before building. The project has not been compiled in this cloud workspace.
5. Keyboard: WASD move, 1–6 punch, Space high guard, C body guard, Q slip, E roll, P/Escape pause. On phones use the onscreen pad and punch/defense buttons; rotate for landscape. MODE changes between rounds. A lost browser/app focus pauses the round. Audio starts after Start Round.
6. Use **TNG → Build Web game**. It generates a scene and exports to `frontend/public/boxing-unity`. Only a successful Unity build writes `manifest.json`; the existing admin game then automatically offers **Play Unity version**. Run the normal frontend build and deploy the generated files to make it live. Web builds can be large; check download size and mobile memory before deploying.
7. Optional APK: **TNG → Build Android APK** creates a development APK under `unity/TngBoxing/Builds`. This is for private device testing, not a signed store release. Preserve any existing InBody/Clover device software; do not install on those business devices for game testing.

Command-line Web build from the repository root:

```powershell
$unityEditor = 'C:\Program Files\Unity\Hub\Editor\6000.0.32f1\Editor\Unity.exe'
& $unityEditor -batchmode -quit -projectPath "$PWD\unity\TngBoxing" -executeMethod TNG.Boxing.Editor.TngBuild.Web -logFile "$PWD\unity-web-build.log"
if ($LASTEXITCODE -ne 0) { throw 'Unity build failed — review unity-web-build.log' }
```

An activated Editor license and installed target module are required. `TNG_UNITY_WEB_OUTPUT` may override the output path. Do not publish a manifest manually or copy partial/failed build outputs. Before release, verify a full round, pause/resume, all six punches, range/misses, defense, combination reset, portrait/landscape, touch cancellation, fullscreen, loading failures and memory on actual iPhone/Android devices. Unity Web support varies by device/browser; use a tested native Android build if the browser is unsuitable. No actual hardware performance or Unity compilation is claimed here.

## Asset conversion and privacy

`python unity/tools/convert_boxer.py` deterministically converts the existing GLB into Unity's JsonUtility format, reflecting Z/winding and preserving all weights. The Unity runtime builds a `SkinnedMeshRenderer` directly. Source is CC0; license/credits are in `TngBoxing/Assets/Licenses`. No MakeHuman application code is included. The scene is local, uses a generic avatar, and has no member/customer data, network calls, purchases, ads, analytics or external AI. Admin-only access in TNGOS is retained; static game assets contain no secrets.
