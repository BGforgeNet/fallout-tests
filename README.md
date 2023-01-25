### Fallout tests

This action allows to check for inconsistencies in `scripts.h`, `scripts.lst`, `*.ssl`, `*.msg` files.

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

| name          | required | default                    | description                         |
| ------------- | -------- | -------------------------- | ----------------------------------- |
| scripts_h     | false    | ""                         | `scripts.h` path                      |
| scripts_lst   | false    | `data/scripts/scripts.lst` | `scripts.lst` path                  |
| scripts_dir   | false    | ""                         | scripts directory                   |
| dialog_dir    | false    | `data/text/english/dialog` | `text/english/dialog` path          |
| check_scripts | false    | true                       | check `scripts.h` and `scripts.lst` |
| check_lvars   | false    | true                       | check LVARs vs `scripts.lst`        |
| check_msgs    | false    | true                       | check msg references in scripts     |
