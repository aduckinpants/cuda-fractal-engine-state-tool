# Packet V8 Manual Fixture Inventory

Date: 2026-08-01

## Purpose and boundary

This is a read-only inventory of the 20 manual captures made from 2026-07-24
through 2026-07-31. It exists to support a dedicated user fixture-selection
turn for the Packet V8 web-session gate.

No fixture is selected or ranked here. No Packet V8 directory has been
generated from these captures. Capture files and the CUDA engine repository
remain unchanged.

## Inventory

All paths are relative to:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture
```

The pipeline column reports the enabled function IDs recorded in the captured
`fractal-state.json`. It is descriptive evidence for selection, not a new
authority surface.

| Capture | Selector | Iterations | Auto | Zoom | Render | Enabled pipeline | Frame |
| --- | --- | ---: | :---: | ---: | --- | --- | ---: |
| `2026-07-24/081527_492__explaino_balance_void` | `explaino_balance_void` | 500 | no | 14.421 | 4096x2563 | `banded_signal > offset_scale > banded_heatmap > balance_void_grade` | 3.4 MB |
| `2026-07-24/085333_309__explaino_balance_void` | `explaino_balance_void` | 500 | no | 14.421 | 4096x2563 | `banded_signal > offset_scale > banded_heatmap > balance_void_grade` | 3.4 MB |
| `2026-07-24/090604_402__explaino_balance_void` | `explaino_balance_void` | 5000 | no | 14.421 | 4096x2560 | `banded_signal > offset_scale > banded_heatmap > balance_void_grade` | 3.1 MB |
| `2026-07-24/091541_635__explaino_balance_void` | `explaino_balance_void` | 60 | no | 334.93 | 4096x2560 | `banded_signal > identity > banded_heatmap > balance_void_grade` | 8.9 MB |
| `2026-07-24/093816_244__explaino_fold` | `explaino_fold` | 397 | no | 1 | 4096x2557 | `smooth_escape_ramp > root_proximity > identity > explaino_cmap > heatmap > grade_glow` | 4.4 MB |
| `2026-07-26/203618_455__explaino` | `explaino` | 500 | no | 2 | 4096x2560 | `root_index > identity > joy_root_palette > basin_default` | 0.4 MB |
| `2026-07-26/210614_504__explaino_mult` | `explaino_mult` | 500 | no | 9,412.3 | 4096x2560 | `smooth_escape_ramp > root_proximity > escape_magnitude > identity > heatmap > explaino_cmap > contrast_lift` | 5.5 MB |
| `2026-07-28/085727_238__explaino_y` | `explaino_y` | 650 | no | 2.8531 | 4096x3071 | `root_index > identity > joy > basin_default` | 0.1 MB |
| `2026-07-30/155813_114__explaino_all` | `explaino_all` | 500 | no | 49.785 | 4096x2559 | `smooth_escape_ramp > root_proximity > escape_magnitude > log_compress > smooth_window > heatmap > grade_glow` | 6.7 MB |
| `2026-07-30/220919_229__explaino_all` | `explaino_all` | 500 | no | 5.7318e6 | 4096x2562 | `smooth_escape_ramp > root_proximity > escape_magnitude > log_compress > smooth_window > heatmap > grade_glow` | 0.2 MB |
| `2026-07-30/222449_767__explaino_all` | `explaino_all` | 500 | no | 34.899 | 4096x2560 | `smooth_escape_ramp > root_proximity > escape_magnitude > log_compress > mirror_repeat > heatmap > heatmap > explaino_cmap > tone_map_finish > grade_glow` | 10.3 MB |
| `2026-07-31/095824_403__explaino_mult` | `explaino_mult` | 500 | no | 17.449 | 4096x2560 | `root_index > identity > joy_root_palette > tone_map_finish` | 0.1 MB |
| `2026-07-31/100017_104__explaino_mult` | `explaino_mult` | 500 | no | 35,743 | 4096x2560 | `root_index > identity > joy_root_palette > tone_map_finish` | 0.1 MB |
| `2026-07-31/101452_110__explaino_mult` | `explaino_mult` | 500 | no | 6.7576e6 | 4096x2557 | `root_index > identity > joy_root_palette > tone_map_finish` | <0.1 MB |
| `2026-07-31/101758_333__explaino_mult` | `explaino_mult` | 500 | no | 0.62092 | 4096x2566 | `root_index > identity > joy_root_palette > tone_map_finish` | 0.1 MB |
| `2026-07-31/102054_224__explaino_mult` | `explaino_mult` | 500 | no | 8.1403 | 4096x2557 | `root_index > identity > joy_root_palette > tone_map_finish` | 0.2 MB |
| `2026-07-31/102406_915__explaino_mult` | `explaino_mult` | 500 | no | 189.06 | 4096x2555 | `root_index > identity > joy_root_palette > tone_map_finish` | 0.2 MB |
| `2026-07-31/102459_588__explaino_mult` | `explaino_mult` | 500 | no | 2,726.4 | 4096x2554 | `root_index > identity > joy_root_palette > tone_map_finish` | 0.1 MB |
| `2026-07-31/102646_638__explaino_mult` | `explaino_mult` | 500 | no | 3.4523 | 4096x2560 | `root_index > identity > joy_root_palette > tone_map_finish` | 0.2 MB |
| `2026-07-31/103522_405__explaino_mult` | `explaino_mult` | 360 | yes | 129.13 | 4096x2559 | `root_index > identity > joy_root_palette > tone_map_finish` | 2.9 MB |

Every inventoried capture has `state.json`, `fractal-state.json`,
`field-notes.md`, and a PNG frame. The inventory deliberately does not infer
visual quality or mathematical interest from filenames, state, pipeline
complexity, frame size, or zoom alone.

## Selection dimensions visible in the inventory

These are neutral distinctions for the review turn, not fixture choices:

- selector breadth: six selectors are represented;
- iteration contrast: 60, 360 with auto-iteration, 397, 500, 650, and 5000;
- camera scale: zoom ranges from 0.62092 through approximately 6.76 million;
- Color Pipeline complexity: simple four-function basin pipelines, multi-source
  pipelines, and one ten-function captured graph;
- transport stress: PNG sizes range from below 0.1 MB through 10.3 MB before
  Packet V8 creates its bounded web derivative;
- comparison clusters: four `explaino_balance_void` captures and nine
  `explaino_mult` captures can support related-state selection if desired,
  while the singleton selectors offer broader novelty.

## User-owned next boundary

The next action is user selection of the captures and intended stress questions
for the Packet V8 manual web-session gate. Packet generation remains on hold
until that selection is explicit. After selection, the implementation agent may
generate only the chosen immutable Packet V8 directories, record their paths and
hashes, prepare the exact prompts/checklist, and stop for external user testing.
