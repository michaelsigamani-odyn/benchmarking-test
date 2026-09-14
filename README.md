# Odyn multi-vendor prediction engine

This repository demonstrates a repeatable cross-OEM training workflow: train on one vendor's hardware, transfer checkpoint artifacts, and resume on a different machine or vendor, while profiling key metrics along the way.

Analytical models of AI/ML training cost exist, but the noise in real systems is too large for them to be deterministic. Instead, we profile a representative sample with a small set of key metrics and fit a regression to the observed behaviour. The working assumption is that the relevant latent factors (hardware characteristics, interconnect, workload shape) can be captured by a low-dimensional representation that the regressor learns from the profiled data.

**What the repository covers:**

- Train, transfer checkpoint artifacts, and resume on a different machine or vendor
- Profile runtime and hardware metrics during training
- Fit a regression model on those metrics to predict training time
- Hardware exercised so far: AMD MI300X, AMD Radeon, and NVIDIA DGX Spark, connected via QSFP

The current scope is intentionally sequential, with a single active training phase at a time. This is a deliberate choice to prove portability and recovery semantics first; data-parallel and multi-job orchestration can be layered on top later.

## Prerequisites

- Python 3.12
- SSH access to participating machines (key-based authentication preferred)
- `conda` or another environment manager

Optional:

- `sshpass` (only if password-based SSH is unavoidable)
- Vendor GPU telemetry libraries (`nvidia-ml-py` and/or the AMD SMI Python bindings)

## Quickstart

```bash
python3 --version
conda create -y -n cross-oem-migration python=3.12
conda activate cross-oem-migration

dg dev -w workspace.yaml
```

Navigate to localhost on the browser to materialize the job/assets, and inspect the run metadata.

<img width="1292" height="821" alt="run" src="https://github.com/user-attachments/assets/1bc13f06-a445-4d03-81b1-2f9d3c13415d" />



## Which metrics, and what's the importance?

Every GPU on Earth obeys the same physics: an operation is limited either by how fast it can compute or by how fast it can move bytes. Our predictor makes that explicit with a roofline-style latency model:


pred_ms = max(flops / (eta_compute * peak_tflops),
              bytes / (eta_bw * mem_bw)) + intercept

Whichever bottleneck is slower wins. The efficiency terms (eta_compute, eta_bw) capture how far a real workload falls short of the datasheet, and the intercept absorbs fixed launch and synchronization overhead.

### Validating the model

A model that is never tested against reality is an opinion. We run an ablation study with three variants:

Profile-only — learned purely from measured runs.
Hardware-prior-only — driven purely by published device specifications.
Hybrid — profiles plus priors.

Each is scored by mean absolute error (MAE) on held-out configurations and held-out devices, so we learn not just how well it fits, but how well it generalizes.

### Why metric selection matters most

Right now, choosing the right metrics is the most consequential decision in this repository. The goal is a set of comparable, normalized measurements that mean the same thing on an NVIDIA host as they do on an AMD host. Without that, cross-vendor comparisons are storytelling, not science.

### Core metrics saved

Training tokens processed
Runtime (seconds)
Throughput (tokens/second)
Average and peak GPU power (watts)
GPU energy (joules)
Efficiency (tokens/joule)
Checkpoint transfer throughput

The part of this cross-OEM work most likely to be useful to the wider community is unifying `amd-smi` and `nvidia-smi` so that the same metrics are gathered on both platforms, despite the different tools. From there, the loop is: validate the accuracy of what was recorded, use it, refine it, and repeat until the most discriminating factors for predicting training time emerge.

Measuring checkpoint transfer speed with `psutil` is equally important. It is what lets us answer whether disaggregating the KV cache between prefill and decode actually pays off, once the time lost waiting for data to cross the public internet is taken into account.


---


