# Export MKS (PTC) Integrity to GIT
* This python script will export the project history from MKS (PTC) Integrity to a GIT repository
* Currently imports checkpoints and development paths only
* This does not currently support incremental imports

## HOW TO USE
1. You must have python and si (mks command line tools) on the PATH variable
2. make a folder for where you want your git repository to reside
3. initialize the git repository by running "git init"
4. next being the import -- from cygwin ```./mks_checkpoints_to_git.py <MKS_project_path> | git fast-import``` and from windows ```python mks_checkpoints_to_git.py <MKS_project_path> | git fast-import```
