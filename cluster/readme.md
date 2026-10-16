# Cluster Job Submission: Usage Guide and Requirements

This folder contains the `submit` scripts required to send jobs to the cluster. This `README` explains how to use them, the requirements that must be met both locally and on the cluster, and how the involved files and folders are structured.

---

## Execution Requirements

### 1. Expected location of `.sh` files

The scripts do not depend on the working directory: every path inside them is absolute
(`$HOME/dd-suite-dev/...` for the code and `$HOME/dd-suite-results/...` for the outputs), and
each script `cd`s into the implementation folder it needs. They can therefore be submitted from
anywhere, e.g.

`sbatch ./dd-suite-dev/cluster/dry_run_submit.sh`

What they do assume is that the repository is cloned at `$HOME/dd-suite-dev`. Update the paths
inside the `.sh` files if it lives somewhere else.

---

### 2. Required folder structure

The outputs go to `$HOME/dd-suite-results/`, with this structure:

```
$HOME/dd-suite-results/
├── results/
│   ├── cpp/
│   ├── python/
│   └── rust/
│
├── salidas/
│   ├── cpp/
│   ├── python/
│   └── rust/
│
└── timeout_log/
    ├── cpp/
    ├── python/
    └── rust/
```

> Most scripts create `results/` and `timeout_log/` themselves with `mkdir -p`, but **`salidas/` and its
> subfolders must already exist**: `#SBATCH --output` writes there before the script body runs, and SLURM
> does not create the directory. Only `dry_run_submit.sh` and the `submit_soc_table2_*.sh` scripts create it.
>
> These names and locations can be changed, but the corresponding paths must be updated within the `.sh` files.

- `results/`: stores the `.csv` test results.
- `timeout_log/`: stores tests that exceeded the `MAX_TIMEOUT`.
- `salidas/`: contains `.txt` files with the output of each submitted job.

---

### 3. Required dependencies

Ensure the following packages or tools are installed:

| Package/Tool | Recommended Installation                                      |
| ------------ | ------------------------------------------------------------- |
| `bitarray` | `pip install bitarray`                                      |
| `gurobi`   | [Gurobi Instructions](https://www.gurobi.com/documentation/)   |
| `pytest`   | `pip install pytest`                                        |
| `cmake`    | >= 3.29                                                       |
| `RUST`     | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs` |

#### Installing Gurobi on the cluster

Follow the steps below to install **Gurobi 13.0.2** in your cluster environment.

##### Download Gurobi

From the terminal, run:

```bash
wget https://packages.gurobi.com/13.0/gurobi13.0.2_linux64.tar.gz
```

This will download the installer to your current directory.

##### Extract the archive

```bash
tar -xvzf gurobi13.0.2_linux64.tar.gz
```

This will create a folder like:

```
gurobi1302/linux64/
```

##### Rename and relocate (optional)

You can rename or move the extracted folder:

```bash
mv gurobi1302 ~/gurobi
```

##### Clean up

Remove the downloaded installer:

```bash
rm gurobi11.0.1_linux64.tar.gz
```

##### Add the license

Copy your license file into the Gurobi folder:

```bash
cp gurobi.lic ~/gurobi/
```

##### Set the environment variable

Add the following line at the end of your `~/.bashrc`:

```bash
export GUROBI_LICENSE_FILE=~/gurobi/gurobi.lic
```

Then, apply the changes:

```bash
source ~/.bashrc
```

---

#### Installing CMake on the Cluster

There are several ways to install or enable `cmake` on the cluster, depending on the environment configuration:

---

##### Option 1: Load via `module` (Recommended if available)

First, check if CMake is available as a module:

```
module avail cmake
```

If you see options like:

```
cmake/3.25.2
cmake/3.29.0
```

You can load it with:

```
module load cmake/3.29.0
```

Then verify:

```
cmake --version
```

> You can add the `module load` command to your `.bashrc` or at the beginning of your job script to make it persistent.

---

##### Option 2: Install via Conda

If using a Conda environment (as is common in many clusters), you can install CMake within it:

First activate the environment if you are not already inside it:

conda activate your_env

and then install the package:

```
conda install -c conda-forge cmake
```

Verify installation:

```
cmake --version
```

> This is useful when you do not have superuser (`sudo`) access.

---

##### Option 3: Build from source (last resort)

If no modules are available and you prefer not to use Conda, you can compile CMake manually:

```
# Step 1: Download and extract CMake (replace version if needed)
wget https://github.com/Kitware/CMake/releases/download/v3.29.2/cmake-3.29.2.tar.gz
tar -xzvf cmake-3.29.2.tar.gz
cd cmake-3.29.2

# Step 2: Build and install locally
./bootstrap --prefix=$HOME/cmake-3.29.2-install
make -j$(nproc)
make install

# Step 3: Add to PATH
export PATH=$HOME/cmake-3.29.2-install/bin:$PATH
```

To make this change permanent, add the `export` line to your `~/.bashrc`.

---

#### Installing RUST on the cluster

To install Rust in your environment, you can use the official installer script provided by the Rust team.

##### Download and run the installer

Run the following command in your terminal:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

This command downloads and runs the **Rust installation script** from the official Rust website. It installs:

- `rustc`: the Rust compiler
- `cargo`: Rust's package manager and build tool
- `rustup`: the Rust toolchain installer and version manager

##### What gets installed

By default, the installation includes:

- The latest stable version of Rust
- Standard libraries
- Documentation (optional)
- Cargo (used to manage dependencies, run builds, and more)

##### Set up the environment

After installation, you may need to configure your environment by adding the following line to your `~/.bashrc` or `~/.zshrc`:

```bash
source $HOME/.cargo/env
```

Alternatively, run it directly in the terminal to load the environment for the current session:

```bash
source $HOME/.cargo/env
```

##### Verify the installation

Check that Rust and Cargo are properly installed:

```bash
which rustc
which cargo
```

You should see paths like:

```
/home/your-user/.cargo/bin/rustc
/home/your-user/.cargo/bin/cargo
```

You can also confirm the version:

```bash
rustc --version
cargo --version
```

### 4. Environment variables

You must define the following environment variables by opening the `~/.bashrc` file using `nano` and adding them at the end of the file.

- `GUROBI_HOME`: path to the installed Gurobi directory. Example:
  ```bash
  export GUROBI_HOME=/home1/USERNAME/gurobi/linux64
  ```
- `HOME`: base path where `.sh` scripts are executed.

In your `CMakeLists.txt`, it's recommended to use:

```cmake
set(GUROBI_INCLUDE_DIRS "$ENV{GUROBI_HOME}/include")
set(GUROBI_LIB_DIRS "$ENV{GUROBI_HOME}/lib")
```

---

## Executing the scripts

To run locally on the cluster or your own computer:

```bash
chmod +x SCRIPT_NAME.sh  # only needed once
./SCRIPT_NAME.sh
```

To create a new script:

```bash
nano new_script.sh
```

Once you're done editing, use the following key combination to save and exit:

```
Ctrl + X → Y → Enter
```

This means:

- `Ctrl + X`: Exit the editor
- `Y`: Confirm you want to save changes (Yes)
- `Enter`: Confirm the file name and save

The output will be shown in the terminal and also saved in the previously mentioned folders.

---

## Script description

### Key variables

- `#SBATCH --partition=tmp`: cluster partition (e.g., `tmp` refers to the one donated by Professor Margarita Castro).
- `#SBATCH --output=salidas/...`: path for log output.
- `#SBATCH --mail-user=...`: to receive job notifications by email, set your address in the `.sh` files.
- `#SBATCH --cpus-per-task=5`: number of CPUs, should match `MAX_PARALLEL`.
- `MAX_PARALLEL=5`: max number of tests running in parallel.
- `MAX_TIMEOUT`: max wall time per test. `5m` for the DD construction scripts; `60m`/`90m` for the Gurobi and SOC cut scripts, whose solver time limit is already one hour.

---

## Verification script: `dry_run_submit.sh`

This script runs a single test per language and is recommended to run first. It checks:

- Dependencies are properly installed.
- Required environment variables are defined.
- Required folders exist.

---

## General cluster usage and useful commands

A cluster is a high-performance computing system composed of multiple connected nodes. It is managed by a **job scheduler** (such as `SLURM`) that assigns user-submitted tasks (jobs) to available nodes.

Job prioritization is handled through a **queue system** based on several factors:

- Available space in the partition.
- Resources requested by the job.
- Estimated job duration.
- User priority (professor, research project, etc.).

### Connecting to the cluster

Connect via SSH using the assigned username:

```bash
ssh USERNAME@cluster.ing.uc.cl
```

Once connected, you'll be asked for your password. Some accounts have Conda environments for isolated package management:

To view all available Conda environments, use:

```bash
conda env list
```

The environment marked with an asterisk (`*`) is the currently active one.

To activate a specific environment:

```bash
conda activate ENV_NAME
```

---

### Uploading and downloading files with `scp`

- **Download from cluster to local:**

```bash
scp USERNAME@cluster.ing.uc.cl:~/file.txt ./local_path/new_file.txt
```

- **Upload from local to cluster:**

```bash
scp file.txt USERNAME@cluster.ing.uc.cl:~/remote_file.txt
```

- **Transfer entire folders:**

```bash
scp -r USERNAME@cluster.ing.uc.cl:~/Results/ ~/Desktop/
```

---

### Connecting to a GitHub Repository via SSH Key

Follow these steps to securely connect to GitHub using an SSH key.

#### Generate a New SSH Key

Run the following command:

```bash
ssh-keygen -t ed25519
```

- Press **Enter** to accept the default location (`~/.ssh/id_ed25519`)
- You can leave the passphrase empty, or enter one for additional security

This will generate:

- A **private key**: `~/.ssh/id_ed25519`
- A **public key**: `~/.ssh/id_ed25519.pub`

#### Copy Your Public Key

To display the contents of your public key, run:

```bash
cat ~/.ssh/id_ed25519.pub
```

Copy the entire output (it starts with `ssh-ed25519 ...`)

#### Add the SSH Key to GitHub

1. Go to [https://github.com/settings/keys](https://github.com/settings/keys)
2. Click on **New SSH key**
3. Enter a title (e.g., `cluster`)
4. Paste the public key you copied
5. Click **Add SSH key**

#### Verify the Connection

Back in your terminal (e.g., on the cluster), run:

```bash
ssh -T git@github.com
```

The first time, it may ask if you trust `github.com`. Type `yes`.

If successful, you should see something like:

```
Hi your-username! You've successfully authenticated, but GitHub does not provide shell access.
```

#### Clone the Repository

You can now clone repositories using the SSH URL:

```bash
git clone git@github.com:your-username/your-repo.git
```

---

### Using FileZilla (GUI)

A visual alternative is [FileZilla](https://filezilla-project.org/), using SFTP:

- Host: `sftp://cluster.ing.uc.cl`
- User: `USERNAME`
- Password: (same as your cluster account)
- Port: `22`

You can drag and drop files between local and remote directories.

---

## Submitting jobs with `sbatch`

To submit a job:

```bash
sbatch SCRIPT_NAME.sh
```

The script must:

1. Start with:

```bash
#!/bin/bash
```

2. Contain SLURM directives like:

```bash
#SBATCH --job-name=dd-batch-cpp-tmp-1
#SBATCH --output=salidas/cpp/output_%j.txt
#SBATCH --error=salidas/cpp/error_%j.txt
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=5
#SBATCH --partition=tmp
```

3. Contain the commands to run:

```bash
echo "Starting job..."
python3 script_test.py
```

---

### Job monitoring commands

- View queued jobs:

  ```bash
  squeue
  squeue -u $USER
  ```
- Submit a job:

  ```bash
  sbatch script_name.sh
  ```
- View node status:

  ```bash
  sinfo
  sinfo -N -o "%.10N %.10O %.10e %.20C"
  ```
- Inspect a job:

  ```bash
  scontrol show job <job_id>
  ```
- Cancel a job:

  ```bash
  scancel <job_id>
  ```
- Exit the cluster:

  ```bash
  exit
  ```
- Join a job's node with `srun`:

  ```bash
  srun --jobid=<id> --pty bash
  htop
  ```
- Use `htop` filters:

  - Press `u` to filter by user
  - Use `/` to search
  - Sort by `%CPU`, `%MEM`
- View logs in real-time:

  ```bash
  tail -f output_file.txt
  ```
- View past jobs:

  ```bash
  sacct -u $USER --format=JobID,JobName,Partition,State,Elapsed,Submit,Start,End
  ```
  To filter by the last 30 days and show a condensed view (job-level only, no steps):

  ```bash
  sacct -u $USER -X --starttime=now-30days --format=JobID,JobName%25,State,Elapsed
  ```
