# TNG Boxing 3D asset attribution

The bundled `boxer-rig-v1.glb` is a derived, clothed game model prepared from MakeHuman's explicitly CC0-released base mesh, default rig/weights and adult male macro targets. It does not represent a particular real fighter.

Source project: https://github.com/makehumancommunity/makehuman

Sources retrieved November 24, 2026:

- `makehuman/data/3dobjs/base.obj` → local source name `body`
- `makehuman/data/rigs/default.mhskel` → `rig`
- `makehuman/data/rigs/default_weights.mhw` → `weights`
- `makehuman/data/targets/macrodetails/caucasian-male-young.target`
- `makehuman/data/targets/macrodetails/african-male-young.target`
- `makehuman/data/targets/macrodetails/asian-male-young.target`
- `makehuman/data/targets/macrodetails/universal-male-young-maxmuscle-averageweight.target`
- `makehuman/data/targets/macrodetails/universal-male-young-averagemuscle-averageweight.target`
- `LICENSE.ASSETS.md` → `CC0-1.0.txt`

The base mesh and target headers explicitly record their CC0 release in September 2020; the rig and weights identify CC0 in their metadata. Original asset contributors include Manuel Bastioni, Data Collection AB, Joel Palmius and Jonas Hauquier. Full license text is included in `CC0-1.0.txt`. Source SHA-256 hashes are stored in `boxer-rig-v1.json`.

TNG modifications: adult macro blending; scale normalization; helper-mesh exclusion; reduced 19-bone skeleton and four-influence weights; clothing material regions; replacement hands/feet for gloves/boots; runtime athlete-kit shading, eyes and boxing equipment; procedural stance and two-bone IK animation. No MakeHuman application source code is embedded in the game.

Rebuild, with the source assets saved under the names above:

```sh
python frontend/scripts/prepare-boxer-asset.py SOURCE_DIRECTORY /tmp/boxer-processed.json
node frontend/scripts/export-boxer-asset.mjs /tmp/boxer-processed.json frontend/public/game/assets
```

The distributed rig contains 9,055 vertices and 16,198 triangles and is about 600 KB. It has no remote buffer/image dependencies. The asset is committed; ordinary application builds do not download or rebuild it.

Rendering library: Three.js 0.187.0, MIT License. Copyright Three.js authors; license included in `THREE-LICENSE.txt`. TNG logos, canvas branding, procedural gear/environment, game code and other project assets retain their respective rights.
