# Executor and preflight contract

## Machine-local executor file

Use [../assets/executor-config.example.json](../assets/executor-config.example.json) as a template. Store the real file as `.researchcenter.local.json`; it must remain gitignored.

An executor defines:

- a local identifier and OS;
- logical connection names mapped to absolute machine paths;
- command aliases such as `python`, `nvidia-smi`, `npu-smi`, or `UnrealEditor-Cmd`;
- non-secret capability metadata.

Do not store SSH keys, passwords, API tokens, signed URLs, or cloud credentials.

## Preflight boundary

Preflight may:

- compare required OS with the current OS;
- resolve required commands without invoking research code;
- check that mapped code/data directories exist;
- call `nvidia-smi` or Ascend `npu-smi info -l` with read-only query arguments and a short timeout;
- report missing or unresolved requirements.

Preflight must not reserve a GPU, install dependencies, start UE, load the dataset, create output directories, or launch an experiment.

Passing preflight means the declared requirements were observable at that moment. It does not reserve resources and does not prove the experiment will succeed.

## Portability

Canonical experiment records refer to logical connections, for example `citysample-code`, instead of `D:\...` or `/mnt/...`. Each executor maps the logical name locally. Keep portable repository records separate from machine-local paths.
