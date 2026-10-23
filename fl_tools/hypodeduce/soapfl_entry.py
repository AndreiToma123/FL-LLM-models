"""Run SoapFL's own run.py with the HypoDeduce chain. Started by the runner with cwd = SoapFL folder.

SoapFL's code is not changed: our phase classes are registered in `chatdev.phase` and `get_config` is
pointed at the generated HypoDeduce configuration, then SoapFL's `main()` runs as usual (same checkout,
fact extraction, checkpoints, result.json). Usage (the runner builds this command):

    python -m fl_tools.hypodeduce.soapfl_entry --config HypoDeduce --version 1.4.0 --project Lang --bugID 1 \
        --output /abs/results/run --model LOCAL
"""
import os
import sys
import tempfile


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    soapfl_dir = os.environ.get("SOAPFL_DIR") or os.getcwd()
    if not os.path.exists(os.path.join(soapfl_dir, "run.py")):
        sys.exit(f"SoapFL not found in {soapfl_dir} (run from the SoapFL folder or set SOAPFL_DIR)")
    os.chdir(soapfl_dir)
    sys.path.insert(0, soapfl_dir)

    from fl_tools.hypodeduce.config import build_configs, existing_configs

    import chatdev.phase as phase_module
    from fl_tools.hypodeduce import phases
    for name in phases.PHASES:
        setattr(phase_module, name, getattr(phases, name))

    import run as soapfl_run
    config_root = os.environ.get("SOAPFL_HD_CONFIG_DIR")
    # the runner writes the configs once before starting the workers; only build them when run on its own
    paths = (existing_configs(config_root) if config_root else None) or \
        build_configs(soapfl_dir, config_root or tempfile.mkdtemp(prefix="hypodeduce-"))
    soapfl_run.get_config = lambda company: paths
    sys.argv = [os.path.join(soapfl_dir, "run.py")] + argv
    soapfl_run.main()


if __name__ == "__main__":
    main()
