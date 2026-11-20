import { mkdir, copyFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
const dist = dirname(fileURLToPath(import.meta.resolve('maplibre-gl')));
const target = new URL('../public/maplibre/', import.meta.url);
await mkdir(target, { recursive: true });
for (const file of ['maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs']) {
  await copyFile(join(dist, file), new URL(file, target));
}
