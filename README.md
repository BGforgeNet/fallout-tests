### Fallout tests

This action allows to search for inconsistencies in `scripts.h`, `scripts.lst`, `*.ssl`, `*.msg` files.

#### Usage

```yaml
- name: Fallout tests
  uses: BGforgeNet/fallout-tests@master
  with:
    scripts_h: scripts_src/headers/scripts.h
    scripts_lst: data/scripts/scripts.lst
    scripts_dir: scripts_src
    dialog_dir: data/text/english/dialog
    worldmap_path: data/data/worldmap.txt
    worldmap_script_sets: 100,101  200,201,202
```

#### Inputs

| name                   | default                         | description                         |
| ---------------------- | ------------------------------- | ----------------------------------- |
| `scripts_h`            | `scripts_src/headers/scripts.h` | `scripts.h` path                    |
| `scripts_lst`          | `data/scripts/scripts.lst`      | `scripts.lst` path                  |
| `scripts_dir`          | `scripts_src`                   | scripts directory                   |
| `dialog_dir`           | `data/text/english/dialog`      | `text/english/dialog` path          |
| `check_scripts`        | `true`                          | check `scripts.h` and `scripts.lst` |
| `check_lvars`          | `true`                          | check LVARs vs `scripts.lst`        |
| `check_msgs`           | `true`                          | check @ `msg` references in scripts |
| `worldmap_path`        | `false`                         | path to `worldmap.txt`              |
| `worldmap_script_sets` | `false`                         | allowed script sets in an encounter |
