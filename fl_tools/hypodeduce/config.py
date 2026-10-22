"""Build the SoapFL configuration files for the HypoDeduce chain (plain JSON, no SoapFL import)."""
import hashlib
import json
import os
from typing import Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_NAME = "HypoDeduce"          # SoapFL takes the config name from the folder name


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def prompts_digest() -> str:
    """Hash of our chain and prompts, recorded in run_meta.json so a run never mixes prompt versions."""
    h = hashlib.sha256()
    for name in ("chain.json", "phases.json"):
        with open(os.path.join(HERE, "config", name), "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:16]


def build_configs(soapfl_dir: str, dest_root: str) -> Tuple[str, str, str]:
    """Write <dest_root>/HypoDeduce/{ChatChainConfig,PhaseConfig,RoleConfig}.json and return their paths.

    ChatChainConfig = SoapFL's default with our phase chain; PhaseConfig = SoapFL's default phases plus ours
    ('inherit' copies a SoapFL phase's roles and prompt); RoleConfig = SoapFL's default.
    """
    default = os.path.join(soapfl_dir, "Config", "Default")
    chain = _load(os.path.join(default, "ChatChainConfig.json"))
    chain["chain"] = _load(os.path.join(HERE, "config", "chain.json"))["chain"]
    phases = _load(os.path.join(default, "PhaseConfig.json"))
    for name, spec in _load(os.path.join(HERE, "config", "phases.json")).items():
        if name.startswith("_"):
            continue
        phases[name] = dict(phases[spec["inherit"]]) if "inherit" in spec else spec
    roles = _load(os.path.join(default, "RoleConfig.json"))

    out_dir = os.path.join(dest_root, CONFIG_NAME)
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for name, data in (("ChatChainConfig.json", chain), ("PhaseConfig.json", phases), ("RoleConfig.json", roles)):
        path = os.path.join(out_dir, name)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)      # atomic: parallel workers may read while another writes
        paths.append(path)
    return tuple(paths)
