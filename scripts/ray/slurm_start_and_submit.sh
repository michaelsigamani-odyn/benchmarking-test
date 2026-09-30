#!/bin/bash
#SBATCH --nodes=2
#SBATCH --exclusive
#SBATCH --time=02:00:00

set -euo pipefail

gpus_per_node=${GPUS_PER_NODE:-8}
head_port=${RAY_HEAD_PORT:-6379}
dashboard_port=${RAY_DASHBOARD_PORT:-8265}
min_worker_port=${RAY_MIN_WORKER_PORT:-10001}
max_worker_port=${RAY_MAX_WORKER_PORT:-10257}
redis_port=${RAY_REDIS_PORT:-6380}
runtime_config=${RAY_RUNTIME_CONFIG:-configs/ray_resilient_local.json}
entrypoint_script=${RAY_ENTRYPOINT_SCRIPT:-scripts/ray/resilient_coordinator.py}
working_dir=${RAY_WORKING_DIR:-.}
status_path=${RAY_STATUS_PATH:-}
python_bin=${PYTHON_BIN:-python3}
zapier_eval_enabled=${ZAPIER_EVAL_ENABLED:-1}
zapier_eval_ssh=${JAX_ZAPIER_EVAL_SSH:-michael@odyn-dgx3}
zapier_eval_root=${JAX_ZAPIER_EVAL_ROOT:-/home/michael/merlin-eval-harness}
zapier_checkpoint_root=${JAX_ZAPIER_CHECKPOINT_ROOT:-/tmp/opencode/bench}

if [[ "$zapier_eval_enabled" == "1" ]]; then
  ssh "$zapier_eval_ssh" "cd $zapier_eval_root && PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' && PYTHONPATH=src python3 -m eval_harness.benchmarks.runner --backend baseline --checkpoint-root $zapier_checkpoint_root --steps 6 && PYTHONPATH=src python3 -m eval_harness.benchmarks.runner --backend baseline --checkpoint-root $zapier_checkpoint_root --steps 10 --resume"
fi

nodes=$(scontrol show hostnames "$SLURM_JOB_NODELIST")
nodes_array=($nodes)
head_node=${nodes_array[0]}
head_node_ip=$(srun --nodes=1 --ntasks=1 -w "$head_node" hostname -I | awk '{print $1}')
ip_head=$head_node_ip:$head_port

srun --nodes=1 --ntasks=1 -w "$head_node" bash -lc "redis-server --bind $head_node_ip --port $redis_port --protected-mode no --daemonize yes"
export REDIS_ADDR=$head_node_ip:$redis_port

srun --nodes=1 --ntasks=1 -w "$head_node" bash -lc "CUDA_VISIBLE_DEVICES='' ray start --head --node-ip-address=$head_node_ip --port=$head_port --dashboard-port=$dashboard_port --block" &
sleep 8

export NGPUS=$((gpus_per_node * SLURM_JOB_NUM_NODES))
for node_i in "${nodes_array[@]}"; do
  srun --exact --nodes=1 --ntasks=1 --cpus-per-task=$((16 * gpus_per_node)) -w "$node_i" \
    ray start --address "$ip_head" \
      --resources="{\"worker_units\": $gpus_per_node}" \
      --min-worker-port=$min_worker_port \
      --max-worker-port=$max_worker_port \
      --block &
  sleep 3
done

until srun --overlap --nodes=1 --ntasks=1 -w "$head_node" ray status | grep -q "worker_units"; do
  sleep 2
done

launch_cmd=(
  "$python_bin" scripts/ray/launch_ray_job.py
  --dashboard-url "http://127.0.0.1:$dashboard_port"
  --entrypoint-script "$entrypoint_script"
  --runtime-config "$runtime_config"
  --working-dir "$working_dir"
)

if [[ -n "$status_path" ]]; then
  launch_cmd+=(--status-path "$status_path")
fi

srun --overlap --nodes=1 --ntasks=1 -w "$head_node" "${launch_cmd[@]}"
