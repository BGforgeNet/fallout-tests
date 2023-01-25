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
```

#### Inputs

| name            | required | default                         | description                         |
| --------------- | -------- | ------------------------------- | ----------------------------------- |
| `scripts_h`     | no       | `scripts_src/headers/scripts.h` | `scripts.h` path                    |
| `scripts_lst`   | no       | `data/scripts/scripts.lst`      | `scripts.lst` path                  |
| `scripts_dir`   | no       | `scripts_src`                   | scripts directory                   |
| `dialog_dir`    | no       | `data/text/english/dialog`      | `text/english/dialog` path          |
| `check_scripts` | no       | `true`                          | check `scripts.h` and `scripts.lst` |
| `check_lvars`   | no       | `true`                          | check LVARs vs `scripts.lst`        |
| `check_msgs`    | no       | `true`                          | check @ `msg` references in scripts |
