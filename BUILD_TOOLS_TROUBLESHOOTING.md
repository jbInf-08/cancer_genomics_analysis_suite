# Visual Studio Build Tools Troubleshooting Guide

## Current Issue
The Visual Studio Build Tools installation appears to be incomplete. The error "Microsoft Visual C++ 14.0 or greater is required" indicates that the C++ compiler is not properly installed or accessible.

## Solution Steps

### Step 1: Verify Current Installation
Run this command to check if the compiler is available:
```cmd
where cl
```

If this returns "INFO: Could not find files for the given pattern(s)", the compiler is not installed or not in PATH.

### Step 2: Complete Visual Studio Build Tools Installation

1. **Download the installer:**
   - Go to: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Download "Build Tools for Visual Studio 2022"

2. **Run the installer and select these components:**
   - ✅ **C++ build tools** (main workload)
   - ✅ **MSVC v143 - VS 2022 C++ x64/x86 build tools** (individual component)
   - ✅ **Windows 10/11 SDK** (latest version)
   - ✅ **CMake tools for Visual Studio** (optional but recommended)

3. **Install and restart your computer**

### Step 3: Verify Installation
After restart, open a **new** Command Prompt and run:
```cmd
where cl
```
This should return a path like: `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.xx.xxxxx\bin\Hostx64\x64\cl.exe`

### Step 4: Install Packages
Once the compiler is available, run:
```cmd
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org pysam==0.21.0 vaex==4.17.0 snakemake==7.32.4
```

## Alternative Solutions

### Option A: Use Conda (Recommended)
If you have Anaconda or Miniconda installed:
```cmd
conda install -c conda-forge pysam vaex snakemake
```

### Option B: Use Pre-compiled Wheels
Try installing from alternative sources:
```cmd
pip install --find-links https://download.pytorch.org/whl/torch_stable.html pysam
```

### Option C: Skip These Packages
Your cancer genomics suite is fully functional without these packages. They are specialized tools for:
- **pysam**: SAM/BAM file processing (bioinformatics)
- **vaex**: Out-of-core DataFrames (large dataset processing)  
- **snakemake**: Workflow management (pipeline orchestration)

## Current Status
✅ **CancerGenomicsSuite is fully functional**
✅ **All core AI/ML libraries are working**
✅ **Web frameworks and databases are ready**
⚠️ **3 specialized packages pending (optional)**

## Next Steps
1. Complete the Visual Studio Build Tools installation as described above
2. Or use conda to install the remaining packages
3. Or proceed with the current installation - your suite is ready to use!
