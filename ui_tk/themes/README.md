# Theme JSON Format

Each theme is configured by a JSON file in this folder.

File naming:
- `forest_light.json` -> theme id `forest-light`
- `forest_dark.json` -> theme id `forest-dark`

Required keys:
- `id` (`string`)
- `base_ttk_theme` (`string`): one of vendor Forest themes (`forest-light` / `forest-dark`)
- `colors` (`object`)
- `roles` (`object`)
- `icons` (`object`)

Required `colors` keys:
- `surface_bg`
- `surface_panel`
- `text_primary`
- `text_muted`
- `accent`
- `accent_hover`
- `selection_bg`
- `selection_fg`
- `border`
- `danger`
- `warning`
- `info`
- `success`

Required `roles` keys:
- `admin`
- `head`
- `teamlead`
- `curator`
- `executor`

`icons` keys:
- `palette`: `light` or `dark` (maps to `ui_tk/assets/icons/<palette>/`)

If theme file is missing or invalid, app falls back to `forest-light`.
