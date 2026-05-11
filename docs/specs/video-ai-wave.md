## Spec update — file paths and asset filenames

The previous spec referenced paths and filenames that don't match how the
assets were actually organized. Update all references in the kinetic
typography HTML files to match the actual filesystem layout.

## Path change

OLD path (in previous spec):
  docs/video/kinetic/_shared/images/[subfolder]/

ACTUAL path (use this):
  video/images/[subfolder]/

The video assets directory lives at the project root under `video/`, not
nested under `docs/video/kinetic/_shared/`. The HTML files themselves still
live at docs/video/kinetic/, so image references from the HTML are:

  ../../../video/images/ai-wave/01-goldman.png

Or restructure the HTML output location to live alongside the assets if
that's cleaner — Jeff's call. Default to keeping HTML at docs/video/kinetic/
and use relative paths.

## AI Wave smash cut — corrected file list

The AI Wave smash cut now uses 5 images, not 6. The second Goldman Sachs
article was dropped because it was redundant with the first.

Folder: video/images/ai-wave/

| Order | Filename              | Content                                                  |
| ----- | --------------------- | -------------------------------------------------------- |
| 1     | 01-goldman.png        | Goldman Sachs — How Will AI Affect the Global Workforce? |
| 2     | 02-worklytics.png     | Worklytics — AI Adoption Benchmarks 2025                 |
| 3     | 03-mckinsey-40.png    | Robotics & Automation News — McKinsey 40% by 2030        |
| 4     | 04-mckinsey-57.png    | Medium — McKinsey's November 2025 Bombshell: 57%         |
| 5     | 05-fortune-altman.png | Fortune — Sam Altman / AI washing                        |

## Timing change for Beat 0e (AI Wave smash cut)

Previous spec: 6 images at 0.6s each (3.6s + transitions = 8s total).
New spec: 5 images, slightly longer per-image to fill the available time.

| Image                 | Display window                                    |
| --------------------- | ------------------------------------------------- |
| 01-goldman.png        | 0:16.0 – 0:16.7 (0.7s)                            |
| 02-worklytics.png     | 0:16.7 – 0:17.4 (0.7s)                            |
| 03-mckinsey-40.png    | 0:17.4 – 0:18.1 (0.7s)                            |
| 04-mckinsey-57.png    | 0:18.1 – 0:18.8 (0.7s)                            |
| 05-fortune-altman.png | 0:18.8 – 0:19.7 (0.9s — held longer as punchline) |

After image 05 (0:19.7–0:24.0): smooth fade to black over ~4 seconds.
This timing recovers ~3.5 seconds vs. the previous 6-image spec — Jeff
will reclaim that elsewhere in the video.

## CSS smash cut implementation (updated for 5 images)

.smashcut-ai-wave img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
}

.smashcut-ai-wave img:nth-child(1) {
  animation: cut 0.7s steps(1) 16.0s forwards;
}
.smashcut-ai-wave img:nth-child(2) {
  animation: cut 0.7s steps(1) 16.7s forwards;
}
.smashcut-ai-wave img:nth-child(3) {
  animation: cut 0.7s steps(1) 17.4s forwards;
}
.smashcut-ai-wave img:nth-child(4) {
  animation: cut 0.7s steps(1) 18.1s forwards;
}
.smashcut-ai-wave img:nth-child(5) {
  animation: cut 0.9s steps(1) 18.8s forwards;
}

@keyframes cut {
  0% { opacity: 0; }
  100% { opacity: 1; }
}

## Other smash cut folder paths (forward reference)

When financial, vibes, rich-kids, and counselor smash cuts are implemented
later, expect the same path convention:

  video/images/financial/
  video/images/vibes/
  video/images/rich-kids/
  video/images/counselor/

Filenames in those folders will follow the same NN-descriptive-name.png
convention with the spec list as the canonical reference.