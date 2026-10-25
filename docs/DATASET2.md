# Dataset 2: the bugs Defects4J 2.0 added (`--dataset d4j2new`)

**What:** the 444 bugs that Defects4J 2.0 added to version 1.4.0: 11 new projects (Cli 39, Codec 18, Collections 4,
Compress 47, Csv 16, Gson 18, JacksonCore 26, JacksonDatabind 112, JacksonXml 6, Jsoup 93, JxPath 22) plus the new
Closure bugs 134-176 (43). Dataset 1 (`d4j14`, the default) stays SoapFL's 388 Defects4J 1.4.0 bugs.

**Why this one:** SoapFL ships a Defects4J 2.0 overlay (`Defects4J_mod/defects4j-2.0.0-jvm-mod`) and a (commented out)
2.0 bug table in its `run_all.py`, so the same tool chain runs unchanged; FlexFL and FaR-Loc also evaluate on
Defects4J 2.0 bugs. Limitation: same benchmark family and same era (pre-2020 bugs), so it tests generalisation
to new projects, not freedom from training-data leakage.

**Defects4J version:** commit `4c41759` (2022-08-25, between v2.0.0 and v2.0.1). It is the exact base of SoapFL's
2.0 overlay: the only differences between that commit and the overlay are SoapFL's own changes (JVM arguments for
its instrumentation agent). Result folders are named `d4j2.0.0-<Project>-<id>` like SoapFL. Java 8 (Defects4J 2.x
requires 1.8). Installed in the image as `/opt/defects4j-2` (`DEFECTS4J2_HOME`), next to `/opt/defects4j` (1.4.0);
project repositories and Major are shared with the 1.4.0 install. The image build checks out and compiles Cli-1
(must work) and one bug of every other new project (informative: `cat /opt/defects4j-2/BUILD_CHECK.txt`).

**Bug list:** the active bugs of that commit (`framework/projects/<P>/active-bugs.csv`). SoapFL's own commented
table leaves out Gson, JacksonCore and Jsoup 1-45 without saying why; we keep them and report infrastructure
failures per project.

**Sampling:** `--pilot N` / `--n N` on dataset 2 uses a corrected largest-remainder allocation (one extra bug per
project per round). Dataset 1 keeps the old rule so the 100 baseline bugs stay the same; that rule gives one project
all extra bugs (the 100-bug sample has Mockito 13 instead of a proportional 10).

**Commands**

```
docker compose build                                                      # once: adds Defects4J 2.0 to the image
docker compose run --rm soapfl cat /opt/defects4j-2/BUILD_CHECK.txt
docker compose run --rm soapfl python -m fl_tools list-bugs --dataset d4j2new --pilot 12
.\run-experiment.cmd qwen25coder -Dataset d4j2new -N 12                   # local pilot: 1 bug per project
csc/submit.sh qwen25coder --smoke --dataset d4j2new                       # CSC: Cli-1 on the test partition
csc/submit.sh qwen25coder --dataset d4j2new --n all                       # CSC: all 444 bugs
```

The selection framework works on these runs unchanged; use `--split none` (the dev/test split belongs to dataset
1, so dataset 2 is a fully held-out replication of the frozen selector S8a+S2).
