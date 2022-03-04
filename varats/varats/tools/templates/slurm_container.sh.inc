{% raw %}#!/bin/bash
#SBATCH -o /dev/null
#SBATCH --ntasks {{ ntasks|default(1) }}
#SBATCH --cpus-per-task {{ cpus|default(1) }}
{% if max_running > 0 %}
#SBATCH --array=0-{{ projects|length() - 1 }}%{{ max_running }}
{% else %}
#SBATCH --array=0-{{ projects|length() - 1 }}
{% endif %}
{# FIXME: Still requires support for max running #}
{{ sbatch_options }}

# Available variables:
# --------------------
# config: BB config in the form of env var export statements
# clean_lockdir:
# clean_lockfile:
# cpus: cpus per task
# lockfile:
# log: slurm log file base name
# max_running: max number of parallel jobs
# name: name of the job
# nice_clean: niceness value for clean job
# node_command:
# ntasks: number of parallel tasks
# prefix: directory on the cluster where BB is run from
# projects: list of project-version combinations to run
# slurm_account: slurm account to use
# slurm_partition: slurm partition to use
# sbatch_options: additional options to pass to sbatch

# List of available projects
projects=(
{% for p in projects %}
'{{ p }}'
{% endfor %}
)
# End of list of available projects
_project="${projects[$SLURM_ARRAY_TASK_ID]}"

exec 1> {{ log }}-$_project
exec 2>&1

# parent of node dir (= BB_SLURM_NODE_DIR) is used as home
node_dir=$(dirname {{ prefix }})

# Prepare cluster node
exec 9> {{ lockfile }}
flock -x 9 && {
  if [ ! -d '{{ prefix }}' ]; then
    echo "$(date) [$(hostname)] prepare local node"
    mkdir -p '{{ prefix }}'
  fi
  rm '{{ lockfile }}'
}
exec 9>&-
# End of prepare cluster node

# Configuration
{% endraw %}
{% for line in vara_config %}
{{ line }}
{% endfor %}
{% raw %}
{% for line in config %}
{{ line }}
{% endfor %}
# End of configuration

scontrol update JobId=${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID} JobName="{{ name }} $_project"
srun -c 1 hostname

# SLURM Command
export XDG_RUNTIME_DIR=${node_dir}
export HOME=${node_dir}
export BB_CONTAINER_ROOT="${node_dir}/containers/lib"
export BB_CONTAINER_RUNROOT="${node_dir}/containers/run"
pushd '{{ prefix }}' > /dev/null
_project=$(echo ${_project} | sed -e "s/-/\//")
{{ node_command }}
popd > /dev/null

# clean up local directory
srun chmod -R u+w ${node_dir} > /dev/null
srun rm -rf ${node_dir}
{% endraw %}
