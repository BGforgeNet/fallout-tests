### Fallout tests

A GitHub Action that checks Fallout 1/2 modding data for inconsistencies: `scripts.h`, `scripts.lst`,
`*.ssl`, `*.msg`, `city.txt`, `maps.txt`, `worldmap.txt`, `quests.txt` and map `.gam` files.

#### Usage

```yaml
- name: Fallout tests
  uses: BGforgeNet/fallout-tests@main # no tags are published; pin a commit SHA to freeze the version
  with:
    scripts_h: scripts_src/headers/scripts.h
    scripts_lst: data/scripts/scripts.lst
    scripts_dir: scripts_src
    dialog_dir: data/text/english/dialog
    city_path: data/data/city.txt
    maps_path: data/data/maps.txt
    worldmap_path: data/data/worldmap.txt
    worldmap_script_sets: |
      100 101
      200 201 202
    quests_path: data/data/quests.txt
    map_gam_dir: data/maps
```

#### Inputs

| name | default | description |
| ---- | ------- | ----------- |
| `scripts_h` | `scripts_src/headers/scripts.h` | `scripts.h` path |
| `scripts_lst` | `data/scripts/scripts.lst` | `scripts.lst` path |
| `scripts_dir` | `scripts_src` | scripts directory |
| `dialog_dir` | `data/text/english/dialog` | dialog `.msg` directory |
| `check_scripts` | `true` | check `scripts.h` against `scripts.lst` |
| `check_lvars` | `true` | check LVARs against `scripts.lst`, and that scripts using the `modreact.h` reaction LVARs keep indices 0-3 free |
| `check_msgs` | `true` | check `.msg` references in scripts |
| `city_path` | `""` | `city.txt` path; empty or `false` skips the check. With `maps_path` set too, entrance map names are checked against `maps.txt` |
| `maps_path` | `""` | `maps.txt` path; empty or `false` skips the check |
| `worldmap_path` | `""` | `worldmap.txt` path; empty or `false` skips the check. Also checks that encounter tables name defined encounters and that `Script:N` is within `scripts_lst` |
| `worldmap_script_sets` | `""` | script sets allowed to share an encounter, one set per line; `#` and `;` start a comment |
| `quests_path` | `""` | `quests.txt` path; empty or `false` skips the check. Reads `vault13.gam` beside it, and `quests.msg` and `map.msg` from `game_msg_dir` |
| `game_msg_dir` | `data/text/english/game` | game `.msg` directory |
| `map_gam_dir` | `""` | directory of map `.gam` files; empty or `false` skips the check. Map headers are read from `scripts_dir/headers` |
